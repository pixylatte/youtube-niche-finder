#!/usr/bin/env bash
# YouTube Brain UI v1 -> v2. Frontend files only; no container or DB changes.
# Invocation: bash <(git show FETCH_HEAD:scripts/upgrade-youtube-brain-ui-v2.sh) TARGET PREVIOUS BASE
set -Eeuo pipefail
umask 077
APP=/opt/youtube-niche-finder
TARGET="${1:-}"; PREVIOUS="${2:-}"; BASE="${3:-}"
fail() { printf 'UI V2 RELEASE BLOCKED: %s\n' "$1" >&2; exit 1; }
for sha in "$TARGET" "$PREVIOUS" "$BASE"; do
  [[ "$sha" =~ ^[a-f0-9]{40}$ ]] || fail "Expected three full pinned Git commit SHAs"
done
for cmd in git tar curl mktemp python3 cp; do command -v "$cmd" >/dev/null || fail "Missing command $cmd"; done
[[ -d "$APP/.git" && -d "$APP/frontend" && -w "$APP/frontend" ]] || fail "Expected writable production checkout missing"
[[ "$(git -C "$APP" rev-parse HEAD)" == "$BASE" ]] || fail "Repository base is not the reviewed version"
[[ "$(git -C "$APP" rev-parse FETCH_HEAD)" == "$TARGET" ]] || fail "Fetched commit does not match target"
git -C "$APP" merge-base --is-ancestor "$PREVIOUS" "$TARGET" || fail "Target is not a descendant of reviewed v1"
curl -fsS --max-time 8 http://127.0.0.1:18080/api/health >/dev/null || fail "Current backend health check failed"

stage="$(mktemp -d)"
mkdir -p "$stage/previous" "$stage/next"
applied=0
backup=''
cleanup() {
  if [[ "$applied" == 1 && -n "$backup" && -s "$backup" ]]; then
    echo "UI V2 health check failed. Restoring previous frontend from $backup" >&2
    tar -xzf "$backup" -C "$APP/frontend" || true
  fi
  rm -rf -- "$stage"
}
trap cleanup EXIT

git -C "$APP" archive "$PREVIOUS" frontend | tar -xf - -C "$stage/previous"
git -C "$APP" archive "$TARGET" frontend | tar -xf - -C "$stage/next"
[[ -f "$stage/next/frontend/index.html" ]] || fail "New release frontend missing"
[[ -f "$stage/previous/frontend/index.html" ]] || fail "Previous frontend missing"

# Only accept a live frontend that still matches the previously deployed v1.
# This catches ad-hoc changes and the intentional dirty Git working tree after v1.
python3 - "$stage/previous/frontend" "$APP/frontend" "$stage/next/frontend" <<'PY'
import filecmp, sys
from pathlib import Path
previous, live, target = map(Path, sys.argv[1:])
for p in previous.rglob("*"):
    relative = p.relative_to(previous)
    current = live / relative
    if p.is_symlink() or not (p.is_dir() or p.is_file()):
        raise SystemExit("UI V2 RELEASE BLOCKED: prior release has an unsafe path")
    if p.is_file() and (not current.is_file() or current.is_symlink() or
                        not filecmp.cmp(p, current, shallow=False)):
        raise SystemExit("UI V2 RELEASE BLOCKED: live frontend differs from v1: " + str(relative))
for p in target.rglob("*"):
    if p.is_symlink() or not (p.is_dir() or p.is_file()):
        raise SystemExit("UI V2 RELEASE BLOCKED: target release has an unsafe path")
html = (target / "index.html").read_text(encoding="utf-8")
if ('data-group="research"' not in html or 'id="langSelect"' not in html or
        'styles.css?v=yb-ui-v2' not in html):
    raise SystemExit("UI V2 RELEASE BLOCKED: expected v2 interface not present")
print("v1 live frontend byte comparison: PASS")
PY

if command -v node >/dev/null; then
  while IFS= read -r -d '' js; do
    node --input-type=module --check < "$js" >/dev/null || fail "ES module syntax failed"
  done < <(find "$stage/next/frontend" -type f -name '*.js' -print0)
  echo "ES module syntax: PASS"
else
  echo "ES module syntax: SKIPPED (Node not installed); run browser checks" >&2
fi

backups="${HOME}/youtube-brain-backups"
mkdir -p "$backups"
backup="$backups/frontend-before-ui-v2-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
tar -czf "$backup" -C "$APP/frontend" .
[[ -s "$backup" ]] || fail "Unable to create backup"
applied=1
cp -a "$stage/next/frontend/." "$APP/frontend/"
curl -fsS --max-time 8 -o "$stage/home.html" http://127.0.0.1:18080/ || fail "Web page not served"
grep -Fq 'id="langSelect"' "$stage/home.html" || fail "New language selector not served"
grep -Fq 'data-group="research"' "$stage/home.html" || fail "Grouped navigation not served"
curl -fsS --max-time 8 -o "$stage/styles.css" 'http://127.0.0.1:18080/styles.css?v=yb-ui-v2' || fail "Stylesheet unavailable"
grep -Fq 'YouTube Brain v2 | navigation groups' "$stage/styles.css" || fail "New styles not served"
curl -fsS --max-time 8 http://127.0.0.1:18080/api/health >/dev/null || fail "API unhealthy after UI release"
applied=0
echo "UI V2 RELEASE OK: 4 navigation groups, locale selector, legible dashboard"
echo "Backup: $backup"
echo "Production DB / Docker / API / MCP / worker remain unchanged."
