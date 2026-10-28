"""Read-only daily research leads, scoped to two deliberately named niche sets."""
from application import search as Q
from domain import daily_decisions as D


def daily_decisions(profile="kayip", period="30d", limit=5):
    D.validate(profile, period, limit)
    niches = D.select_niches(Q.list_niches(), profile)
    videos = []
    # Only local Postgres/embedding-derived video metrics. No quota-spending
    # collector, LLM, OAuth account, or public source verification.
    for niche in niches:
        results = Q.search_outliers(
            niche=niche["slug"], period=period,
            only_shorts=D.PROFILES[profile]["only_shorts"],
            exclude_shorts=not D.PROFILES[profile]["only_shorts"],
            limit=60, sort_by="outlier",
        )
        for video in results:
            videos.append({**video, "nicheSlug": niche["slug"],
                           "nicheLabel": niche["label"]})
    return D.rank(profile, period, limit, niches, videos)
