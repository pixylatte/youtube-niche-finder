"""Editor-preparation checks: no YouTube calls, no external verification."""
import pytest

from domain import editorial_readiness as E


def review(profile="kayip"):
    return {
        "profile": profile,
        "referenceTitle": "Osmanlı döneminde kuşatma teknolojileri",
        "angle": "Kuşatma teknolojilerinin tarihsel kaynaklardaki anlatım farkları",
        "effort": "medium",
        "claimsReviewed": True,
        "rightsReviewed": True,
        "sources": [
            {"url": "https://arsiv.gov.tr/belge", "type": "archive", "reviewed": True},
            {"url": "https://universite.edu.tr/makale", "type": "academic", "reviewed": True},
        ],
    }


def test_history_review_can_be_prepared_but_no_verified_source_claim():
    result = E.evaluate(review())
    assert result["status"] == "prepared-for-human-editorial-review"
    assert result["uniqueReviewedSourceDomains"] == 2
    assert result["sourcesVerifiedExternally"] is False
    assert result["factsVerifiedExternally"] is False
    assert result["rightsClearedBySystem"] is False
    assert result["assessment"] == "self-reported-completeness-only"
    assert result["youtubeQuotaUsed"] == 0
    assert result["blockers"] == []


def test_islam_requires_scriptural_or_scholarly_source_type():
    payload = review("islam")
    missing = E.evaluate(payload)
    assert "profile-specific-source-type-required" in missing["blockers"]
    payload["sources"][0]["type"] = "quran"
    ready = E.evaluate(payload)
    assert ready["status"] == "prepared-for-human-editorial-review"


def test_two_references_on_same_domain_are_not_independent():
    payload = review()
    payload["sources"][1]["url"] = "https://www.arsiv.gov.tr/different"
    result = E.evaluate(payload)
    assert result["uniqueReviewedSourceDomains"] == 1
    assert "two-independent-source-domains-required" in result["blockers"]


def test_unreviewed_and_video_reference_links_are_not_fact_sources():
    payload = review()
    payload["sources"][0]["url"] = "https://youtube.com/watch?v=abcdefghijk"
    payload["sources"][1]["reviewed"] = False
    result = E.evaluate(payload)
    assert result["uniqueReviewedSourceDomains"] == 0
    assert result["status"] == "research-incomplete"


def test_reused_reference_title_is_not_an_original_angle():
    payload = review()
    payload["angle"] = payload["referenceTitle"]
    result = E.evaluate(payload)
    assert result["originalAngleProvided"] is False
    assert "original-angle-required" in result["blockers"]


def test_empty_human_assertions_and_unknown_effort_remain_incomplete():
    payload = review()
    payload.update(claimsReviewed=False, rightsReviewed=False, effort="unknown")
    result = E.evaluate(payload)
    assert "human-claim-review-required" in result["blockers"]
    assert "rights-and-licenses-review-required" in result["blockers"]
    assert "production-effort-estimate-required" in result["blockers"]


@pytest.mark.parametrize("url", [
    "http://example.org/a",
    "javascript:alert(1)",
    "https://127.0.0.1/a",
    "https://localhost/a",
    "https://user:pass@example.org/document",
    "https://example.local/page",
    "https://example.org " + "x" * 500,
])
def test_bad_or_internal_source_urls_are_rejected(url):
    payload = review()
    payload["sources"][0]["url"] = url
    with pytest.raises(ValueError):
        E.evaluate(payload)


@pytest.mark.parametrize("modifier", [
    lambda p: p.update(profile="unknown"),
    lambda p: p.update(effort="free"),
    lambda p: p.update(claimsReviewed="yes"),
    lambda p: p.update(rightsReviewed=1),
    lambda p: p.update(sources="https://example.org"),
    lambda p: p.update(sources=p["sources"] * 4),
    lambda p: p["sources"][0].update(type="fake"),
    lambda p: p["sources"][0].update(reviewed="yes"),
    lambda p: p.update(angle="x" * 1201),
])
def test_bad_payloads_are_rejected(modifier):
    payload = review()
    modifier(payload)
    with pytest.raises(ValueError):
        E.evaluate(payload)


def test_source_full_urls_are_not_reflected_in_review_response():
    payload = review()
    payload["sources"][0]["url"] = "https://arsiv.gov.tr/private-editorial-note"
    result = E.evaluate(payload)
    assert "private-editorial-note" not in str(result)
    assert "arsiv.gov.tr" not in str(result)
    assert result["submittedSources"] == 2
