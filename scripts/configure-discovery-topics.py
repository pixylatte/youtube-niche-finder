#!/usr/bin/env python3
"""Safely opt in to DAILY discovery topics on the SECOND YouTube Brain VDS.

No YouTube API requests happen in this script. By default this is a preview.
Only explicit --apply updates .env and recreates the WORKER container.
The worker will execute its next scheduled daily cycle (possibly tomorrow).
Topics are deliberately capped; vidIQ is not involved.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone


ROOT = Path("/opt/youtube-niche-finder")
ENV_PATH = ROOT / ".env"
BACKUP_DIR = Path("/root/youtube-brain-backups")
MAX_TOPICS = 6


def normalize_topics(values):
    topics = []
    for raw in values:
        value = " ".join(str(raw).split())
        if not 3 <= len(value) <= 80:
            raise ValueError("Each topic must be 3–80 characters")
        if not all(c.isalnum() or c in " -_" for c in value):
            raise ValueError("Use only letters, numbers, spaces, '-' and '_' in topics")
        if value.casefold() not in (old.casefold() for old in topics):
            topics.append(value)
    if not 1 <= len(topics) <= MAX_TOPICS:
        raise ValueError(f"Use 1 to {MAX_TOPICS} unique topics")
    return topics


def update_env(text, topics):
    replacements = {
        "WORKER_QUERIES": ",".join(topics),
        "WORKER_QUERY_PERIOD": "7d",
        "WORKER_QUERY_PAGES": "1",
        "WORKER_DAILY_INTERVAL_MIN": "1440",
    }
    lines = text.splitlines(keepends=True)
    counts = {key: 0 for key in replacements}
    output = []
    for line in lines:
        if line.lstrip().startswith("#"):
            output.append(line)
            continue
        match = re.match(r"^([A-Z_][A-Z_0-9]*)\s*=", line)
        key = match.group(1) if match else None
        if key in replacements:
            counts[key] += 1
            if counts[key] > 1:
                raise ValueError(f"Duplicate active {key} in .env; resolve manually")
            output.append(f"{key}={replacements[key]}\n")
        else:
            output.append(line)
    for key, value in replacements.items():
        if not counts[key]:
            if output and not output[-1].endswith("\n"):
                output.append("\n")
            output.append(f"{key}={value}\n")
    return "".join(output), replacements


def worker_preflight():
    # The worker already exists; do not accidentally start/rebuild a whole
    # production stack, or expose the complete environment in a command log.
    inspect = subprocess.run(
        ["docker", "inspect", "niche-finder-worker"],
        capture_output=True, text=True, check=True,
    )
    entry = json.loads(inspect.stdout)[0]
    if entry["State"].get("Status") != "running":
        raise RuntimeError("Worker is not running; diagnose it before changing .env")
    labels = entry.get("Config", {}).get("Labels", {}) or {}
    if labels.get("com.docker.compose.project") != "niche-finder" or (
            labels.get("com.docker.compose.service") != "worker"):
        raise RuntimeError("Unexpected Docker Compose project/service; deployment blocked")
    configured = labels.get("com.docker.compose.project.config_files")
    if not configured or configured.split(",") != [str(ROOT / "docker-compose.yml")]:
        raise RuntimeError("Worker uses a different Compose configuration; do not recreate it")
    env = dict(line.partition("=")[::2] for line in entry["Config"].get("Env", []))
    if not env.get("YOUTUBE_API_KEY"):
        raise RuntimeError("Worker has no API key; diagnose without exposing the secret")


def write_atomic(path, data):
    fd, tmp = tempfile.mkstemp(prefix=".discovery-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(data)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def recreate_worker():
    subprocess.run(["docker", "compose", "config", "-q"], cwd=ROOT, check=True)
    subprocess.run(
        ["docker", "compose", "up", "-d", "--no-deps", "--force-recreate", "worker"],
        cwd=ROOT, check=True,
    )
    # Running does not mean one discovery scan has completed; that occurs
    # according to worker_last_daily, not on every restart.
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}", "niche-finder-worker"],
        capture_output=True, text=True, check=True,
    )
    if result.stdout.strip() != "running":
        raise RuntimeError("Worker did not enter running state")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="explicitly update .env + worker")
    parser.add_argument("topics", nargs="+", help="1–6 search topics; one search page each per daily cycle")
    args = parser.parse_args()
    topics = normalize_topics(args.topics)
    if not ENV_PATH.is_file() or not (ROOT / "docker-compose.yml").is_file():
        raise SystemExit("Expected second VDS installation/.env not found")
    original = ENV_PATH.read_text(encoding="utf-8")
    revised, values = update_env(original, topics)
    print("Daily discovery topics:", ", ".join(topics))
    print("Topic count:", len(topics), "/ 100 search calls allowed per day")
    print("Worker cadence: 1440 min | period: 7d | 1 page per topic")
    print("Additional search calls per daily cycle:", len(topics))
    print("Approx. next discovery: the next scheduled daily cycle, not necessarily immediately")
    print("No changes to DB, web, MCP, Google quota settings or vidIQ")
    if not args.apply:
        print("DRY RUN ONLY: run with --apply if these values are intended")
        return
    if os.geteuid() != 0:
        raise SystemExit("Use root to apply. Do not chown/chmod the app tree.")
    worker_preflight()
    if revised == original:
        print("Settings already match; worker not restarted")
        return
    BACKUP_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUP_DIR / f"discovery-env-before-{stamp}.bak"
    shutil.copy2(ENV_PATH, backup)
    backup.chmod(0o600)
    changed = False
    try:
        write_atomic(ENV_PATH, revised)
        changed = True
        recreate_worker()
    except Exception:
        if changed:
            # Restore configuration without printing secrets. Also restore
            # the previous container config best-effort.
            write_atomic(ENV_PATH, original)
            try:
                recreate_worker()
            except Exception:
                print("WARNING: worker could not be restored; inspect Docker")
        raise
    print("DISCOVERY CONFIGURED: worker recreated successfully")
    print("Backup saved:", backup)
    print("Note: next scheduled worker daily cycle will trigger search calls")


if __name__ == "__main__":
    main()
