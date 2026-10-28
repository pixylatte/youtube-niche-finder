"""Pure zero-quota evidence ranking for the two editorial workspaces."""
import pytest

from domain import daily_decisions as D


def item(id, niche="kayıp-sayfalar-osmanlı", channel="UC-Test-1", views=5000,
         outlier=3.2, relative=5.0, is_short=False):
    return {
        "videoId": id, "title": "Archived documentary reference",
        "channelId": channel, "channelTitle": "Archive Creator",
        "nicheSlug": niche, "nicheLabel": "Osmanlı",
        "views": views, "outlierScore": outlier,
        "viewsPerSubscriber": relative, "vph24h": None, "snapshots": 1,
        "isShort": is_short, "publishedAt": "2026-10-20T12:00:00Z",
    }


def test_only_editorially_labeled_niches_are_used():
    data = [
        {"slug": "kayıp-sayfalar-osmanlı", "label": "Osmanlı", "video_count": 40},
        {"slug": "1-dakika-islam-kissalar", "label": "Kıssalar", "video_count": 80},
        {"slug": "trending-tr", "label": "Other", "video_count": 500},
    ]
    assert [x["slug"] for x in D.select_niches(data, "kayip")] == [
        "kayıp-sayfalar-osmanlı"]
    assert [x["slug"] for x in D.select_niches(data, "islam")] == [
        "1-dakika-islam-kissalar"]


def test_no_matching_niches_does_not_invent_video_ideas():
    response = D.rank("islam", "30d", 5, [], [])
    assert response["status"] == "insufficient-data"
    assert response["insufficientReason"] == "no-labelled-niches"
    assert response["candidates"] == []
    assert response["youtubeQuotaUsed"] == 0


def test_no_valid_archived_performance_does_not_become_proven():
    niches = [{"slug": "kayıp-sayfalar-osmanlı"}]
    rows = [item("abcdefghijk", views=120, outlier=None, relative=None)]
    response = D.rank("kayip", "30d", 5, niches, rows)
    assert response["status"] == "insufficient-data"
    assert response["insufficientReason"] == "no-qualified-performance-signal"


def test_ranked_leads_are_distinct_video_and_channel_references():
    niches = [{"slug": "kayıp-sayfalar-osmanlı"}]
    videos = [
        item("abcdefghijk", channel="UC1", outlier=4),
        item("abcdefghijk", channel="UC1", outlier=4),  # same video in two niches
        item("lmnopqrstuv", channel="UC1", outlier=6),  # same creator, should not dominate
        item("0123456789A", channel="UC2", outlier=3),
    ]
    result = D.rank("kayip", "30d", 5, niches, videos)
    assert result["status"] == "research-leads"
    assert result["qualifiedVideoReferences"] == 3
    assert result["selectedDistinctChannels"] == 2
    assert len(result["candidates"]) == 2
    assert {r["channelId"] for r in result["candidates"]} == {"UC1", "UC2"}
    assert all(r["videoUrl"].startswith("https://www.youtube.com/watch?v=")
               for r in result["candidates"])


def test_outlier_and_relative_metrics_are_labeled_not_promised_success():
    row = item("abcdefghijk", outlier=None, relative=4.0)
    result = D.rank("kayip", "30d", 5, [{"slug": row["nicheSlug"]}], [row])
    candidate = result["candidates"][0]
    assert candidate["signal"] == "views-per-subscriber"
    assert candidate["outlierScore"] is None
    assert candidate["vph24h"] is None
    assert candidate["evidence"] == "single-observation-or-missing-velocity"
    assert "not original video proposals" in result["note"]


def test_rejects_bad_identifiers_and_nonfinite_metrics():
    rows = [
        item("javascript:", outlier=99),
        item("abcdefghijk", views=float("nan"), outlier=99),
        item("lmnopqrstuv", outlier=float("inf"), relative=None),
    ]
    result = D.rank("kayip", "7d", 5, [{"slug": "kayıp-sayfalar-osmanlı"}], rows)
    assert result["candidates"] == []


@pytest.mark.parametrize("profile,period,limit", [
    ("other", "30d", 5), ("kayip", "all", 5), ("islam", "7d", 0),
    ("islam", "7d", 9), ("islam", "7d", True),
])
def test_inputs_are_bounded(profile, period, limit):
    with pytest.raises(ValueError):
        D.validate(profile, period, limit)


def test_profile_format_and_source_verification_are_explicit():
    for profile, fmt in [("kayip", "long"), ("islam", "shorts")]:
        result = D.rank(profile, "90d", 5, [], [])
        assert result["format"] == fmt
        assert result["verificationRequired"]
        assert result["provenance"] == "local-archived-youtube-metrics-only"



def test_1_dakika_islam_niche_matches_collector_slugify():
    from application.collecting import slugify

    unicode_slug = slugify("1 Dakika İslam - kıssalar")
    ascii_slug = slugify("1 Dakika Islam - kıssalar")
    assert unicode_slug == "1-dakika-i-slam-kıssalar"
    assert ascii_slug == "1-dakika-islam-kıssalar"
    niches = D.select_niches([
        {"slug": unicode_slug, "video_count": 12},
        {"slug": ascii_slug, "video_count": 8},
        {"slug": "1-dakika-islamiyet-genel", "video_count": 100},
    ], "islam")
    assert {n["slug"] for n in niches} == {unicode_slug, ascii_slug}


def test_cannot_mix_short_and_long_format_or_cross_profile_evidence():
    long_niche = "kayıp-sayfalar-osmanlı"
    short_niche = "1-dakika-islam-kıssalar"
    rows = [
        item("abcdefghijk", niche=long_niche, channel="UC1", is_short=False),
        item("abcdefghijl", niche=short_niche, channel="UC2", is_short=True),
        item("abcdefghijm", niche=short_niche, channel="UC3", is_short=False),
    ]
    short = D.rank("islam", "30d", 8, [{"slug": short_niche}], rows)
    assert [r["videoId"] for r in short["candidates"]] == ["abcdefghijl"]
    long = D.rank("kayip", "30d", 8, [{"slug": long_niche}], rows)
    assert [r["videoId"] for r in long["candidates"]] == ["abcdefghijk"]
