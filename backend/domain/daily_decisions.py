"""Deterministic research leads for two editorial workspaces (zero YouTube quota).

A source video that outperformed its channel is evidence of *an archived
YouTube performance signal*, NOT evidence that the historical/religious claims
are correct and NOT a proven original video idea. No LLM, no invented topics,
no opaque 0-100 "success probability". Nothing is written to the database.
"""
import math
import re
from collections import Counter

PROFILES = {
    "kayip": {
        "name": "Kayıp Sayfalar",
        "prefixes": ("kayıp-sayfalar",),
        "only_shorts": False,
        "verification": "historical-primary-sources-required",
    },
    "islam": {
        "name": "1 Dakika İslam",
        "prefixes": ("1-dakika-i-slam", "1-dakika-islam"),
        "only_shorts": True,
        "verification": "quran-hadith-and-scholarly-verification-required",
    },
}
PERIODS = frozenset(("7d", "30d", "90d"))
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
MAX_NICHES = 16
MAX_RESULTS = 8


def validate(profile, period, limit):
    if profile not in PROFILES:
        raise ValueError("profile must be kayip or islam")
    if period not in PERIODS:
        raise ValueError("period must be 7d, 30d or 90d")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise ValueError("limit must be between 1 and 8")


def select_niches(all_niches, profile):
    """Match deliberately labeled editorial niches; never guess from a title."""
    if profile not in PROFILES:
        raise ValueError("unknown profile")
    prefixes = PROFILES[profile]["prefixes"]
    out = []
    for row in all_niches:
        slug = row.get("slug")
        name = slug.casefold() if isinstance(slug, str) else ""
        if any(name == prefix or name.startswith(prefix + "-") for prefix in prefixes):
            out.append({"slug": slug, "label": str(row.get("label") or slug),
                        "archiveVideos": int(row.get("video_count") or 0)})
    return sorted(out, key=lambda n: (-n["archiveVideos"], n["slug"]))[:MAX_NICHES]


def _number(raw):
    if isinstance(raw, bool):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value >= 0 else None


def _candidate(video):
    video_id = video.get("videoId")
    if not isinstance(video_id, str) or not VIDEO_ID.fullmatch(video_id):
        return None
    title = video.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    outlier = _number(video.get("outlierScore"))
    relative = _number(video.get("viewsPerSubscriber"))
    views = _number(video.get("views"))
    # Neither views alone nor missing metric baselines can qualify a lead.
    if (views is None or views < 200
            or not ((outlier is not None and outlier >= 1.5)
                    or (relative is not None and relative >= 2.0))):
        return None
    vph = _number(video.get("vph24h"))
    snapshots = video.get("snapshots")
    snapshot_count = snapshots if type(snapshots) is int and snapshots >= 0 else 0
    signal = "outlier" if outlier is not None and outlier >= 1.5 else "views-per-subscriber"
    return {
        "videoId": video_id,
        "videoUrl": "https://www.youtube.com/watch?v=" + video_id,
        "referenceTitle": title[:240],
        "channelTitle": str(video.get("channelTitle") or "")[:120],
        "channelId": str(video.get("channelId") or "")[:80],
        "publishedAt": video.get("publishedAt"),
        "nicheSlug": video.get("nicheSlug"),
        "nicheLabel": str(video.get("nicheLabel") or "")[:120],
        "views": int(views),
        "outlierScore": round(outlier, 2) if outlier is not None else None,
        "viewsPerSubscriber": round(relative, 2) if relative is not None else None,
        "vph24h": round(vph, 2) if vph is not None and snapshot_count >= 2 else None,
        "snapshotCount": snapshot_count,
        "signal": signal,
        "evidence": ("snapshot-supported" if snapshot_count >= 2 and vph is not None
                     else "single-observation-or-missing-velocity"),
        "_priority": (1 if outlier is not None and outlier >= 1.5 else 0,
                      min(outlier or 0, 50), min(relative or 0, 100),
                      min(vph if snapshot_count >= 2 and vph is not None else 0, 10000),
                      min(views, 10000000)),
    }


def rank(profile, period, limit, niches, videos):
    """Turn a bounded local corpus into distinct-channel reference leads."""
    validate(profile, period, limit)
    unique = {}
    observed_ids = set()
    allowed_niches = {row["slug"] for row in niches}
    expected_short = PROFILES[profile]["only_shorts"]
    for video in videos:
        # Defensive boundary: never mix evidence across channel workspaces,
        # even if the application caller accidentally passes unfiltered rows.
        if video.get("nicheSlug") not in allowed_niches:
            continue
        if video.get("isShort") is not expected_short:
            continue
        if isinstance(video.get("videoId"), str) and VIDEO_ID.fullmatch(video["videoId"]):
            observed_ids.add(video["videoId"])
        candidate = _candidate(video)
        if not candidate:
            continue
        key = candidate["videoId"]
        if key not in unique or candidate["_priority"] > unique[key]["_priority"]:
            unique[key] = candidate

    ordered = sorted(unique.values(),
                     key=lambda r: (r["_priority"], r["videoId"]), reverse=True)
    selected = []
    seen_channels = set()
    by_niche = Counter()
    for item in ordered:
        # Diversity is deliberate; a viral channel's multiple uploads cannot
        # dominate the whole daily decision list.
        channel = item["channelId"]
        if not channel or channel in seen_channels or by_niche[item["nicheSlug"]] >= 2:
            continue
        seen_channels.add(channel)
        by_niche[item["nicheSlug"]] += 1
        row = dict(item)
        row.pop("_priority")
        selected.append(row)
        if len(selected) >= limit:
            break

    if not niches:
        state, reason = "insufficient-data", "no-labelled-niches"
    elif not videos:
        state, reason = "insufficient-data", "no-videos-in-period-or-format"
    elif not selected:
        state, reason = "insufficient-data", "no-qualified-performance-signal"
    else:
        state, reason = "research-leads", None

    return {
        "profile": profile, "profileName": PROFILES[profile]["name"],
        "period": period, "format": "shorts" if PROFILES[profile]["only_shorts"] else "long",
        "status": state, "insufficientReason": reason,
        "relatedNiches": len(niches),
        "sampleVideos": len(observed_ids),
        "qualifiedVideoReferences": len(unique),
        "selectedDistinctChannels": len(selected),
        "candidates": selected,
        "verificationRequired": PROFILES[profile]["verification"],
        "provenance": "local-archived-youtube-metrics-only",
        "note": ("References are archived videos, not original video proposals. "
                 "Metrics do not validate factual or religious claims; independently "
                 "verify primary sources, originality and rights before production."),
        "youtubeQuotaUsed": 0,
    }
