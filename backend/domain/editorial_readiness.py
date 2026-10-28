"""Human editorial preparation gate for YouTube Brain reference leads.

This does NOT verify webpages, historical facts, religious interpretations,
copyright, or licenses. Source types and review checkboxes are user assertions,
not machine-verification claims. No external calls, persistence or API quota.
"""
import ipaddress
import re
import unicodedata
from urllib.parse import urlsplit

SOURCE_TYPES = frozenset({
    "archive", "museum", "academic", "official", "quran", "hadith",
    "scholarly", "other",
})
EFFORT = frozenset({"unknown", "low", "medium", "high"})
MAX_SOURCES = 6
MAX_BODY = 1200
MAX_REFERENCE = 240


def _short_text(raw, maximum):
    if not isinstance(raw, str) or len(raw) > maximum:
        raise ValueError("Invalid text length")
    return raw.strip()


def _domain_from_url(raw):
    url = _short_text(raw, 500)
    if not url:
        raise ValueError("Source URL is required")
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Source must be an HTTPS URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Credentials are not allowed in source URLs")
        host = parsed.hostname.casefold().rstrip(".")
        if len(host) > 253 or "." not in host or host.endswith(".local"):
            raise ValueError("Source host must be a public hostname")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("IP-address sources are not supported")
        if any(ch.isspace() for ch in host):
            raise ValueError("Malformed hostname")
    except (ValueError, AttributeError) as exc:
        raise ValueError("Invalid HTTPS source URL") from exc
    return host.removeprefix("www.")


def _words(value):
    folded = unicodedata.normalize("NFKC", value).casefold()
    return set(re.findall(r"\w+", folded))


def _is_distinct_angle(angle, reference_title):
    if not angle or len(angle) < 30:
        return False
    if not reference_title:
        return True
    angle_words = _words(angle)
    source_words = _words(reference_title)
    if not angle_words:
        return False
    # It must not be a copy or merely the reference title with a short suffix.
    similarity = len(angle_words & source_words) / len(angle_words | source_words)
    additions = angle_words - source_words
    superficial_suffix = source_words.issubset(angle_words) and len(additions) < 4
    return (angle.casefold() != reference_title.casefold()
            and similarity < 0.8 and not superficial_suffix)


def evaluate(payload):
    """Assess only completeness of user-submitted editorial preparation."""
    if not isinstance(payload, dict):
        raise ValueError("An editorial review object is required")
    profile = payload.get("profile")
    if profile not in ("kayip", "islam"):
        raise ValueError("profile must be kayip or islam")

    angle = _short_text(payload.get("angle", ""), MAX_BODY)
    reference_title = _short_text(payload.get("referenceTitle", ""), MAX_REFERENCE)
    effort = payload.get("effort", "unknown")
    if effort not in EFFORT:
        raise ValueError("Invalid effort estimate")
    if type(payload.get("claimsReviewed", False)) is not bool:
        raise ValueError("claimsReviewed must be a boolean")
    if type(payload.get("rightsReviewed", False)) is not bool:
        raise ValueError("rightsReviewed must be a boolean")

    sources = payload.get("sources", [])
    if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
        raise ValueError("At most six sources are supported")
    safe_sources = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("Source must be an object")
        kind = source.get("type")
        if kind not in SOURCE_TYPES:
            raise ValueError("Unrecognized source category")
        if type(source.get("reviewed", False)) is not bool:
            raise ValueError("reviewed must be a boolean")
        host = _domain_from_url(source.get("url"))
        safe_sources.append({"domain": host, "type": kind,
                             "reviewedByUser": source.get("reviewed", False)})

    # A reference video is a competitor example, not independent factual proof.
    reference_hosts = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com")
    reviewed = [
        s for s in safe_sources
        if s["reviewedByUser"] and not any(
            s["domain"] == host or s["domain"].endswith("." + host)
            for host in reference_hosts
        )
    ]
    domains = {s["domain"] for s in reviewed}
    types = {s["type"] for s in reviewed}
    if profile == "kayip":
        relevant_types = {"archive", "museum", "academic", "official"}
    else:
        relevant_types = {"quran", "hadith", "scholarly"}
    blockers = []
    if not _is_distinct_angle(angle, reference_title):
        blockers.append("original-angle-required")
    if len(domains) < 2:
        blockers.append("two-independent-source-domains-required")
    if not types.intersection(relevant_types):
        blockers.append("profile-specific-source-type-required")
    if not payload.get("claimsReviewed", False):
        blockers.append("human-claim-review-required")
    if not payload.get("rightsReviewed", False):
        blockers.append("rights-and-licenses-review-required")
    if effort == "unknown":
        blockers.append("production-effort-estimate-required")

    return {
        "profile": profile,
        "status": "prepared-for-human-editorial-review" if not blockers else "research-incomplete",
        "blockers": blockers,
        "uniqueReviewedSourceDomains": len(domains),
        "userClassifiedSourceTypes": sorted(types),
        "submittedSources": len(safe_sources),
        "originalAngleProvided": _is_distinct_angle(angle, reference_title),
        "userAssertedClaimReview": payload.get("claimsReviewed", False),
        "userAssertedRightsReview": payload.get("rightsReviewed", False),
        "effortEstimate": effort,
        "assessment": "self-reported-completeness-only",
        "sourcesVerifiedExternally": False,
        "factsVerifiedExternally": False,
        "rightsClearedBySystem": False,
        "youtubeQuotaUsed": 0,
        "note": ("Human assertions and source URLs are not independently validated. "
                 "A complete checklist is not approval to publish."),
    }
