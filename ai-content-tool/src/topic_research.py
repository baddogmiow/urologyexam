"""Find candidate topics to make content about.

Primary source is Google Trends (via pytrends). This is best-effort: trends
data is a *signal*, not a guarantee of success, and pytrends can break when
Google changes its internal endpoints. Callers should always allow a manual
``--topic`` override instead of depending on this working.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import settings


@dataclass
class TopicCandidate:
    keyword: str
    source: str
    score: int = 0


def trending_topics(limit: int = 10) -> list[TopicCandidate]:
    """Return trending search terms for the configured region.

    Returns an empty list (never raises) if pytrends is unavailable or the
    request fails, so callers can fall back to a manual topic.
    """
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []

    try:
        pytrends = TrendReq(hl="zh-TW", tz=480)
        df = pytrends.trending_searches(pn=_region_to_pytrends_country(settings.trends_region))
        keywords = df[0].tolist()[:limit]
        return [
            TopicCandidate(keyword=kw, source="google_trends", score=limit - i)
            for i, kw in enumerate(keywords)
        ]
    except Exception:
        # Network blocked, endpoint changed, region unsupported, etc. -
        # topic research is a convenience, not a hard dependency.
        return []


def _region_to_pytrends_country(region_code: str) -> str:
    mapping = {
        "TW": "taiwan",
        "US": "united_states",
        "JP": "japan",
        "HK": "hong_kong",
    }
    return mapping.get(region_code.upper(), "taiwan")


def related_queries(seed_keyword: str, limit: int = 10) -> list[TopicCandidate]:
    """Expand a seed keyword into related search queries, when available."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return []

    try:
        pytrends = TrendReq(hl="zh-TW", tz=480)
        pytrends.build_payload([seed_keyword], timeframe="now 7-d")
        related = pytrends.related_queries()
        rising = related.get(seed_keyword, {}).get("rising")
        if rising is None or rising.empty:
            return []
        rows = rising.head(limit)
        return [
            TopicCandidate(keyword=row["query"], source="related_rising", score=int(row.get("value", 0)))
            for _, row in rows.iterrows()
        ]
    except Exception:
        return []
