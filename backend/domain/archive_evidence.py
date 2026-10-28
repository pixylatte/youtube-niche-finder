"""Conservative quality gate ported conceptually from legacy YouTube Brain.

The legacy opportunity-evidence-quality policy distinguishes strong videos
from *supported evidence*. Here it is adapted to Niche Finder's own cached
niche rows and `niches.last_collected_at`; no legacy data or migrations are
copied. It never changes rankings, calls YouTube, or validates source claims.
"""
from datetime import datetime, timezone
import math
import re

VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
DAY_SECONDS = 86400
FRESH_VIDEO_DAYS = 45
FRESH_COLLECTION_DAYS = 7
MIN_DISTINCT_VIDEOS = 3
MIN_CHANNELS = 2
MIN_RECENT_VIDEOS = 2
MIN_STRONG_RECENT = 1


def _parse_time(value, now):
    if not isinstance(value, str) or not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        stamp = stamp.astimezone(timezone.utc)
        if stamp > now:
            return None
        return stamp
    except (TypeError, ValueError, OverflowError):
        return None


def _strong_score(value):
    if isinstance(value, bool):
        return False
    try:
        score = float(value)
    except (ValueError, TypeError, OverflowError):
        return False
    return math.isfinite(score) and score >= 2


def assess(rows, last_collected_at=None, now=None):
    """Describe the *archived evidence*, not YouTube-wide demand or causality.

    A fresh niche collection is not proof that every channel was scanned.
    Published-at freshness and collection freshness remain separate.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        return {
            "status": "unavailable", "reasons": ["invalid-archive-rows"],
            "quotaUsed": 0, "rankingsChanged": False,
        }

    by_video = {}
    for row in rows:
        video_id = row.get("video_id")
        if isinstance(video_id, str) and VIDEO_ID.fullmatch(video_id):
            by_video[video_id] = row

    distinct_channels = {r.get("channel_id") for r in by_video.values()
                         if isinstance(r.get("channel_id"), str) and r["channel_id"]}
    recent = []
    latest = None
    for row in by_video.values():
        published = _parse_time(row.get("published_at"), now)
        if published is not None:
            if latest is None or published > latest:
                latest = published
            if (now - published).total_seconds() <= FRESH_VIDEO_DAYS * DAY_SECONDS:
                recent.append(row)

    collected = _parse_time(last_collected_at, now)
    collected_days = ((now - collected).total_seconds() / DAY_SECONDS
                      if collected is not None else None)
    latest_days = ((now - latest).total_seconds() / DAY_SECONDS
                   if latest is not None else None)
    recent_strong = sum(1 for r in recent if _strong_score(r.get("outlierScore")))

    reasons = []
    if len(by_video) < MIN_DISTINCT_VIDEOS:
        reasons.append("few-distinct-videos")
    if len(distinct_channels) < MIN_CHANNELS:
        reasons.append("few-independent-channels")
    if len(recent) < MIN_RECENT_VIDEOS:
        reasons.append("few-recent-publications")
    if recent_strong < MIN_STRONG_RECENT:
        reasons.append("no-recent-outlier")
    if latest_days is None:
        reasons.append("publication-dates-unknown")
    if collected_days is None:
        reasons.append("collection-time-unknown")
    elif collected_days > FRESH_COLLECTION_DAYS:
        reasons.append("collection-stale")

    status = ("no-signal" if not by_video else
              "supported-sample" if not reasons else "limited")
    return {
        "status": status,
        "reasons": reasons,
        "distinctVideos": len(by_video),
        "distinctChannels": len(distinct_channels),
        "recentVideos45d": len(recent),
        "recentOutliers2x": recent_strong,
        "latestPublishedAt": latest.isoformat() if latest else None,
        "latestVideoAgeDays": round(latest_days, 1) if latest_days is not None else None,
        "lastCollectedAt": collected.isoformat() if collected else None,
        "lastCollectionAgeDays": round(collected_days, 1)
        if collected_days is not None else None,
        "evidenceScope": "locally-archived-sample",
        "freshnessScope": "niche-collection-event-not-complete-rival-refresh",
        "isSuccessPrediction": False,
        "isIndependentFactVerification": False,
        "rankingsChanged": False,
        "quotaUsed": 0,
    }
