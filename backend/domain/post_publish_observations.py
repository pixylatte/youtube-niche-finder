"""Observed post-publication measurement readiness, adapted from old Brain.

Niche Finder takes irregular, often 3-hour snapshots; never pretend they are
exact 1h/6h/24h/72h checkpoints. Use only observed times and view counters.
No YouTube calls, DB writes, projections or inferred missing measurements.
"""
import math


def _point(row):
    if not isinstance(row, dict):
        return None
    age, views = row.get("ageHours"), row.get("views")
    if isinstance(age, bool) or isinstance(views, bool):
        return None
    if not isinstance(age, (int, float)) or not math.isfinite(age) or age < 0:
        return None
    if not isinstance(views, int) or views < 0:
        return None
    return (float(age), views)


def assess(points, *, comparability_break=False):
    if not isinstance(points, list):
        return {"status": "unavailable", "reason": "invalid-observation-input",
                "snapshotCount": None, "observedFirstDayRate": None,
                "quotaUsed": 0}
    seen = []
    for item in points:
        parsed = _point(item)
        if parsed is not None:
            seen.append(parsed)
    valid = sorted(set(seen))
    if not valid:
        return {"status": "insufficient", "reason": "no-observed-snapshots",
                "snapshotCount": 0, "firstObservedHours": None,
                "lastObservedHours": None, "firstDaySnapshots": 0,
                "observedFirstDayRate": None, "quotaUsed": 0}

    first_day = [p for p in valid if p[0] <= 24]
    interval = None
    if len(first_day) >= 2 and not comparability_break:
        first, last = first_day[0], first_day[-1]
        hours = last[0] - first[0]
        delta = last[1] - first[1]
        if hours >= 1 and delta >= 0:
            interval = {
                "fromHours": first[0], "toHours": last[0],
                "actualHours": round(hours, 2),
                "observedViewGain": delta,
                "viewsPerHour": round(delta / hours, 2),
            }

    return {
        "status": "observed-interval" if interval else "limited",
        "reason": (None if interval else
                   "view-count-definition-change" if comparability_break else
                   "first-day-delta-unavailable-or-not-monotonic"),
        "snapshotCount": len(valid),
        "firstObservedHours": valid[0][0],
        "lastObservedHours": valid[-1][0],
        "firstDaySnapshots": len(first_day),
        "observedFirstDayRate": interval,
        "exactCheckpointsVerified": False,
        "coverage": "observed-snapshot-interval-only",
        "quotaUsed": 0,
        "note": ("Observed change between actual archive snapshots, never "
                 "a claimed exact 24-hour view count or predicted velocity."),
    }
