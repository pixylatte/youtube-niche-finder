"""Zero-quota, no-Docker tests for scheduler evidence display."""
from datetime import datetime, timedelta, timezone

from application.discovery_activity import (
    build_run,
    build_topic_result,
    parse_run,
    parse_topic_result,
    summarize,
)


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
    assert payload["evidenceLevel"] == "recorded-collector-outcomes"
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


def test_topic_watch_summary_counts_real_return_without_owner_ids():
    import json

    raw = build_topic_result("ok", {
        "topicsSearched": 3, "videosStored": 12, "searchCalls": 3,
        "stoppedBy": "search-quota", "skippedUsers": [1, 2],
    }, now=NOW)
    encoded = json.dumps(raw)
    assert '"skippedUsers"' not in encoded
    assert '"user_id"' not in encoded
    parsed = parse_topic_result(encoded, now=NOW)
    assert parsed["topicsSearched"] == 3
    assert parsed["videosStored"] == 12
    assert parsed["searchCalls"] == 3
    assert parsed["skippedOwnerCount"] == 2
    assert parsed["stoppedBy"] == "search-quota"


def test_topic_watch_failures_and_skips_do_not_fake_stored_videos():
    import json

    for state in ("failed", "quota", "skipped", "invalid_result"):
        encoded = json.dumps(build_topic_result(state, now=NOW))
        result = summarize(topic_run_record=encoded, now=NOW)
        assert result["topicSearchRun"]["state"] == state
        assert result["topicSearchRun"]["videosStored"] == 0
        assert result["topicSearchRun"]["topicsSearched"] == 0
        assert result["evidenceLevel"] == "recorded-collector-outcomes"


def test_corrupted_topic_records_fail_closed():
    import json

    assert parse_topic_result('{"state":"ok","token":"private"}', now=NOW) is None
    invalid = build_topic_result("ok", {"topicsSearched": 0, "videosStored": 0,
                                       "searchCalls": 0, "stoppedBy": None}, now=NOW)
    invalid["videosStored"] = -1
    assert parse_topic_result(json.dumps(invalid), now=NOW) is None
    invalid["videosStored"] = 0
    invalid["at"] = {"unexpected": True}
    assert parse_topic_result(json.dumps(invalid), now=NOW) is None
