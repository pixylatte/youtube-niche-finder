"""Zero-quota, no-Docker tests for scheduler evidence display."""
from datetime import datetime, timedelta, timezone

from application.discovery_activity import summarize


NOW = datetime(2026, 10, 28, 9, 30, tzinfo=timezone.utc)


def test_no_worker_markers_does_not_claim_the_worker_is_running():
    result = summarize(now=NOW, calls_today=0, search_limit=100)
    assert result["dailySchedulerMarker"]["state"] == "missing"
    assert result["topicSchedulerMarker"]["state"] == "missing"
    assert result["searchQuota"]["callsLeft"] == 100
    assert result["workerRunningVerified"] is False
    assert result["discoverySuccessVerified"] is False


def test_recent_worker_mark_is_only_a_marker_not_search_success():
    stamp = (NOW - timedelta(hours=1)).isoformat()
    result = summarize(daily_marker=stamp, topic_marker=stamp,
                       calls_today=3, units_today=7, now=NOW)
    assert result["dailySchedulerMarker"]["state"] == "recent"
    assert result["searchQuota"]["callsLeft"] == 97
    assert result["unitQuota"]["unitsLeft"] == 2993
    assert not result["discoverySuccessVerified"]


def test_old_and_invalid_timestamps_are_distinguished():
    old = (NOW - timedelta(days=3)).isoformat()
    result = summarize(daily_marker=old, topic_marker="not a time", now=NOW)
    assert result["dailySchedulerMarker"]["state"] == "stale"
    assert result["topicSchedulerMarker"]["state"] == "invalid"
    assert result["topicSchedulerMarker"]["at"] is None


def test_future_clock_skew_is_not_recent_success():
    future = (NOW + timedelta(minutes=10)).isoformat()
    result = summarize(daily_marker=future, now=NOW)
    assert result["dailySchedulerMarker"]["state"] == "clock_skew"


def test_limits_clamp_without_misreporting_negative_remaining():
    result = summarize(calls_today=101, search_limit=100,
                       units_today=3005, unit_limit=3000, now=NOW)
    assert result["searchQuota"]["callsLeft"] == 0
    assert result["unitQuota"]["unitsLeft"] == 0


def test_naive_timestamp_is_interpreted_as_utc_but_naive_now_is_rejected():
    result = summarize(daily_marker="2026-10-28T09:00:00", now=NOW)
    assert result["dailySchedulerMarker"]["state"] == "recent"
    try:
        summarize(now=datetime(2026, 10, 28))
    except ValueError:
        pass
    else:
        raise AssertionError("Naive now must be rejected")
