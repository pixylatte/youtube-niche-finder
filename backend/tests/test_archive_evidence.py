"""Zero-API tests of legacy Brain evidence-quality ideas adapted to Niche Finder."""
from datetime import datetime, timedelta, timezone

from domain.archive_evidence import assess


NOW = datetime(2026, 10, 28, 11, 0, tzinfo=timezone.utc)


def video(vid, channel="UC-A", days=2, score=2.8):
    return {
        "video_id": vid, "channel_id": channel,
        "published_at": (NOW - timedelta(days=days)).isoformat(),
        "outlierScore": score,
    }


def test_two_rivals_and_recent_archive_are_supported_as_sample_only():
    rows = [
        video("abcdefghijk", "UC-A", 1, 3.1),
        video("lmnopqrstuv", "UC-B", 5, 1.2),
        video("0123456789A", "UC-B", 70, 1.1),
    ]
    result = assess(rows, (NOW - timedelta(hours=4)).isoformat(), now=NOW)
    assert result["status"] == "supported-sample"
    assert result["distinctVideos"] == 3
    assert result["distinctChannels"] == 2
    assert result["recentVideos45d"] == 2
    assert result["recentOutliers2x"] == 1
    assert result["quotaUsed"] == 0
    assert result["rankingsChanged"] is False
    assert result["isSuccessPrediction"] is False
    assert result["isIndependentFactVerification"] is False
    assert result["freshnessScope"] == "niche-collection-event-not-complete-rival-refresh"


def test_one_channel_does_not_prove_independent_rival_interest():
    rows = [
        video("abcdefghijk", "UC-A"),
        video("lmnopqrstuv", "UC-A"),
        video("0123456789A", "UC-A"),
    ]
    result = assess(rows, NOW.isoformat(), now=NOW)
    assert result["status"] == "limited"
    assert "few-independent-channels" in result["reasons"]


def test_old_niche_collection_stays_limited_even_with_new_publications():
    rows = [
        video("abcdefghijk", "UC-A"),
        video("lmnopqrstuv", "UC-B"),
        video("0123456789A", "UC-B"),
    ]
    result = assess(rows, (NOW - timedelta(days=15)).isoformat(), now=NOW)
    assert result["status"] == "limited"
    assert "collection-stale" in result["reasons"]
    assert result["latestVideoAgeDays"] == 2.0
    assert result["lastCollectionAgeDays"] == 15.0


def test_missing_collection_marker_is_unknown_not_zero_age():
    rows = [
        video("abcdefghijk", "UC-A"),
        video("lmnopqrstuv", "UC-B"),
        video("0123456789A", "UC-B"),
    ]
    result = assess(rows, None, now=NOW)
    assert "collection-time-unknown" in result["reasons"]
    assert result["lastCollectionAgeDays"] is None


def test_duplicate_and_bad_video_ids_do_not_inflate_evidence():
    rows = [
        video("abcdefghijk", "UC-A"),
        video("abcdefghijk", "UC-A"),
        video("not-video", "UC-B"),
    ]
    result = assess(rows, NOW.isoformat(), now=NOW)
    assert result["status"] == "limited"
    assert result["distinctVideos"] == 1
    assert "few-distinct-videos" in result["reasons"]


def test_empty_and_invalid_archive_are_not_promoted_to_success():
    result = assess([], NOW.isoformat(), now=NOW)
    assert result["status"] == "no-signal"
    assert result["distinctVideos"] == 0
    assert assess(None, now=NOW)["status"] == "unavailable"
    assert assess([object()], now=NOW)["status"] == "unavailable"


def test_future_or_invalid_timestamps_cannot_make_freshness_appear_good():
    rows = [
        video("abcdefghijk", "UC-A", score=3),
        video("lmnopqrstuv", "UC-B", score=2),
        video("0123456789A", "UC-B", score=1),
    ]
    result = assess(rows, (NOW + timedelta(minutes=5)).isoformat(), now=NOW)
    assert "collection-time-unknown" in result["reasons"]
    assert result["status"] == "limited"


def test_nonfinite_outlier_is_never_a_strong_video():
    rows = [
        video("abcdefghijk", "UC-A", score=float("inf")),
        video("lmnopqrstuv", "UC-B", score=float("nan")),
        video("0123456789A", "UC-B", score=None),
    ]
    result = assess(rows, NOW.isoformat(), now=NOW)
    assert "no-recent-outlier" in result["reasons"]
    assert result["recentOutliers2x"] == 0
