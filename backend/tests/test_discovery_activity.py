"""Zero-quota, no-Docker tests for scheduler evidence display."""
from datetime import datetime, timedelta, timezone

from application.discovery_activity import build_run, parse_run, summarize


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


def test_completed_query_batch_is_evidence_not_new_unique_counts():
    items = [
        {"status": "ok", "videos_found": 10, "videos_stored": 9, "channels_stored": 4},
        {"status": "failed"},
        {"status": "quota"},
        {"status": "skipped"},
        {"status": "invalid_result"},
    ]
    encoded = build_run(items, configured_topics=5, now=NOW)
    assert encoded["attempted"] == 4
    assert encoded["successful"] == 1
    assert encoded["failed"] == 1
    assert encoded["quotaBlocked"] == 1
    assert encoded["skipped"] == 1
    assert encoded["invalidResults"] == 1
    assert encoded["videosFound"] == 10
    assert encoded["videosProcessed"] == 9
    assert encoded["channelProfilesReported"] == 4


def test_latest_batch_is_sanitized_and_integrated_into_read_only_summary():
    import json

    raw = json.dumps(build_run([{"status": "ok", "videos_found": 5}], 1, now=NOW))
    payload = summarize(run_record=raw, now=NOW)
    assert payload["discoveryRun"]["recorded"]["state"] == "recent"
    assert payload["discoveryRun"]["successful"] == 1
    assert payload["workerRunningVerified"] is False
    assert payload["discoverySuccessVerified"] is False
    assert payload["evidenceLevel"] == "schedule-and-query-outcomes"
    assert "query" not in json.dumps(payload).lower()


def test_empty_configured_queries_are_reported_as_zero_not_a_success():
    import json

    raw = json.dumps(build_run([], 0, now=NOW))
    payload = summarize(run_record=raw, now=NOW)
    assert payload["discoveryRun"]["configuredTopics"] == 0
    assert payload["discoveryRun"]["attempted"] == 0
    assert payload["discoveryRun"]["successful"] == 0


def test_malformed_untrusted_run_never_reaches_the_dashboard():
    import json

    good = build_run([{"status": "ok"}], 1, now=NOW)
    bad = {**good, "successful": 200}
    assert parse_run(json.dumps(bad), now=NOW) is None
    assert parse_run('{"token": "secret"}', now=NOW) is None
    assert parse_run("x" * 4097, now=NOW) is None
    assert parse_run(json.dumps([good]), now=NOW) is None
    assert summarize(run_record="{bad", now=NOW)["discoveryRun"] is None


def test_cannot_report_more_results_than_configured_topics():
    import pytest

    with pytest.raises(ValueError):
        build_run([{"status": "ok"}], 0, now=NOW)
    with pytest.raises(ValueError):
        build_run([{"status": "not-a-status"}], 1, now=NOW)
    with pytest.raises(ValueError):
        build_run([{"status": "ok", "videos_found": -1}], 1, now=NOW)
    with pytest.raises(ValueError):
        build_run([{"status": "ok"}] * 101, 101, now=NOW)


def test_old_run_is_stale_even_if_it_was_successful():
    import json

    old = NOW - timedelta(hours=49)
    raw = json.dumps(build_run([{"status": "ok"}], 1, now=old))
    data = summarize(run_record=raw, now=NOW)["discoveryRun"]
    assert data["recorded"]["state"] == "stale"
    assert data["successful"] == 1
