"""Pure tests for the opt-in discovery configuration editor. No network, DB or Docker."""
import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "configure-discovery-topics.py"
SPEC = importlib.util.spec_from_file_location("configure_discovery_topics", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_topics_are_bounded_unique_and_support_turkish():
    assert MODULE.normalize_topics(["  İslam   tarihi ", "islam tarihi",
                                    "Osmanlı tarihi"]) == [
                                        "İslam tarihi", "islam tarihi", "Osmanlı tarihi"]
    assert MODULE.normalize_topics(["İslam tarihi", "İslam tarihi"]) == ["İslam tarihi"]
    with pytest.raises(ValueError):
        MODULE.normalize_topics(["a"] * 3)
    with pytest.raises(ValueError):
        MODULE.normalize_topics([f"topic {i}" for i in range(7)])


@pytest.mark.parametrize("topic", ["", "x", "a,b", "foo=bar", "foo\nbar",
                                   "danger\"\nYOUTUBE_API_KEY=bogus", "<script>"])
def test_discovery_topics_reject_unsafe_text(topic):
    with pytest.raises(ValueError):
        MODULE.normalize_topics([topic])


def test_env_update_changes_only_four_safe_keys_and_preserves_secrets():
    original = (
        "# WORKER_QUERIES=old commented topics\n"
        "YOUTUBE_API_KEY=keep-private-value\n"
        "WORKER_QUERIES=\n"
        "WORKER_QUERY_PAGES=4\n"
        "WORKER_QUERY_PERIOD=24h\n"
        "WORKER_DAILY_INTERVAL_MIN=60\n"
        "DB_PASSWORD=unchanged\n"
    )
    new, changes = MODULE.update_env(
        original, ["İslam tarihi", "Osmanlı tarihi"])
    assert "WORKER_QUERIES=İslam tarihi,Osmanlı tarihi\n" in new
    assert "WORKER_QUERY_PAGES=1\n" in new
    assert "WORKER_QUERY_PERIOD=7d\n" in new
    assert "WORKER_DAILY_INTERVAL_MIN=1440\n" in new
    assert "YOUTUBE_API_KEY=keep-private-value" in new
    assert "DB_PASSWORD=unchanged" in new
    assert "# WORKER_QUERIES=old commented topics" in new
    assert set(changes) == {"WORKER_QUERIES", "WORKER_QUERY_PAGES",
                            "WORKER_QUERY_PERIOD", "WORKER_DAILY_INTERVAL_MIN"}
    updated, _ = MODULE.update_env(new, ["İslam tarihi", "Osmanlı tarihi"])
    assert updated == new


def test_env_writer_appends_missing_keys_without_modifying_others():
    new, _ = MODULE.update_env("YOUTUBE_API_KEY=secret", ["kayıp uygarlıklar"])
    assert new.startswith("YOUTUBE_API_KEY=secret\n")
    assert "WORKER_QUERIES=kayıp uygarlıklar\n" in new


def test_duplicate_live_keys_are_rejected_before_disk_writes():
    with pytest.raises(ValueError, match="Duplicate active WORKER_QUERIES"):
        MODULE.update_env("WORKER_QUERIES=alpha\nWORKER_QUERIES=beta\n",
                          ["osmanlı tarihi"])


def test_active_discovery_is_opt_in():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'if not args.apply:' in text
    assert 'worker_preflight()' in text
    assert 'recreate_worker()' in text
    assert 'write_atomic(ENV_PATH, original)' in text
    assert "import requests" not in text
