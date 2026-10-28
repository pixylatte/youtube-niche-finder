"""Read-only evidence of the discovery scheduler, not proof of successful search.

The worker marks its daily / topic-search timestamps even if a guarded step
failed. Quota counters also include manual calls. Never infer worker liveness,
configured worker topics, or newly discovered channels from these fields.
"""
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


def summarize(*, daily_marker=None, topic_marker=None, calls_today=0,
              search_limit=100, units_today=0, unit_limit=3000, now=None):
    """Summarize locally recorded metadata without network, API or DB writes."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    calls = max(0, int(calls_today))
    units = max(0, int(units_today))
    max_calls = max(0, int(search_limit))
    max_units = max(0, int(unit_limit))
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
        "evidenceLevel": "schedule-metadata-only",
        "workerRunningVerified": False,
        "discoverySuccessVerified": False,
    }
