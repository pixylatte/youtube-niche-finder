"""Read-only evidence of the discovery scheduler, not proof of successful search.

The worker marks its daily / topic-search timestamps even if a guarded step
failed. Quota counters also include manual calls. Never infer worker liveness,
configured worker topics, or newly discovered channels from these fields.
"""
import json
from datetime import datetime, timezone


def _timestamp_evidence(value, now):
    if not value:
        return {"at": None, "state": "missing"}
    if not isinstance(value, str):
        return {"at": None, "state": "invalid"}
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        seconds = (now - timestamp.astimezone(timezone.utc)).total_seconds()
    except (TypeError, ValueError, OverflowError):
        return {"at": None, "state": "invalid"}
    if seconds < -300:
        state = "clock_skew"
    elif seconds > 48 * 3600:
        state = "stale"
    else:
        state = "recent"
    return {"at": timestamp.isoformat(), "state": state}



# A single aggregate record, deliberately without query names, raw search
# responses, credentials, channel IDs, or any potentially sensitive metadata.
OUTCOME_STATUSES = frozenset({"ok", "failed", "quota", "skipped", "invalid_result"})
RUN_FIELDS = ("configuredTopics", "attempted", "successful", "failed", "quotaBlocked",
              "skipped", "invalidResults", "videosFound", "videosProcessed",
              "channelProfilesReported")
MAX_TOPICS = 100


def _nonnegative(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1_000_000:
        raise ValueError("Expected a bounded nonnegative integer")
    return value


def build_run(outcomes, configured_topics, now=None):
    """Sanitized outcomes of one worker WORKER_QUERIES batch.

    'videos_stored' is processed rows, NOT newly inserted distinct videos.
    'channels_stored' is the profiles returned, NOT newly discovered channels.
    No changes are made to YouTube or the local database here.
    """
    when = now or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    configured = _nonnegative(configured_topics)
    if configured > MAX_TOPICS or len(outcomes) != configured:
        raise ValueError("Each configured query must have exactly one outcome")
    counts = {key: 0 for key in RUN_FIELDS}
    counts["configuredTopics"] = configured
    for item in outcomes:
        if not isinstance(item, dict) or item.get("status") not in OUTCOME_STATUSES:
            raise ValueError("Unrecognized outcome")
        state = item["status"]
        if state != "skipped":
            counts["attempted"] += 1
        if state == "ok":
            counts["successful"] += 1
            for source, target in (("videos_found", "videosFound"),
                                   ("videos_stored", "videosProcessed"),
                                   ("channels_stored", "channelProfilesReported")):
                counts[target] += _nonnegative(item.get(source, 0))
        elif state == "failed":
            counts["failed"] += 1
        elif state == "quota":
            counts["quotaBlocked"] += 1
        elif state == "skipped":
            counts["skipped"] += 1
        else:
            counts["invalidResults"] += 1
    return {"at": when.astimezone(timezone.utc).isoformat(), **counts}


def parse_run(raw, now=None):
    """Validate persisted JSON without reflecting unrecognized fields."""
    if not raw or not isinstance(raw, str) or len(raw) > 4096:
        return None
    try:
        loaded = json.loads(raw)
        if not isinstance(loaded, dict):
            return None
        values = {key: _nonnegative(loaded[key]) for key in RUN_FIELDS}
        if (values["configuredTopics"] > MAX_TOPICS
                or values["attempted"] + values["skipped"] != values["configuredTopics"]
                or values["successful"] + values["failed"] + values["quotaBlocked"]
                + values["invalidResults"] != values["attempted"]):
            return None
        if not isinstance(loaded.get("at"), str):
            return None
        instant = _timestamp_evidence(loaded["at"],
                                      now or datetime.now(timezone.utc))
        if instant["state"] in ("missing", "invalid", "clock_skew"):
            return None
        return {"recorded": instant, **values}
    except (KeyError, ValueError, TypeError, OverflowError):
        return None


def summarize(*, daily_marker=None, topic_marker=None, calls_today=0,
              search_limit=100, units_today=0, unit_limit=3000, now=None,
              run_record=None):
    """Summarize locally recorded metadata without network, API or DB writes."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    calls = max(0, int(calls_today))
    units = max(0, int(units_today))
    max_calls = max(0, int(search_limit))
    max_units = max(0, int(unit_limit))
    run = parse_run(run_record, now=now)
    return {
        "observedAt": now.isoformat(),
        "dailySchedulerMarker": _timestamp_evidence(daily_marker, now),
        "topicSchedulerMarker": _timestamp_evidence(topic_marker, now),
        "searchQuota": {
            "callsToday": calls,
            "dailyLimit": max_calls,
            "callsLeft": max(0, max_calls - calls),
        },
        "unitQuota": {
            "unitsToday": units,
            "dailyLimit": max_units,
            "unitsLeft": max(0, max_units - units),
        },
        "discoveryRun": run,
        "evidenceLevel": "schedule-and-query-outcomes" if run
        else "schedule-metadata-only",
        "workerRunningVerified": False,
        "discoverySuccessVerified": False,
    }
