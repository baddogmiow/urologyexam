"""Optional integration with Freesound.org's free sound/music library.

Requires a free API key (https://freesound.org/apiv2/apply/). Downloads
use the "preview" mp3 (available via simple API-key auth; the original
lossless file requires a full OAuth2 login flow, which is overkill for
a CLI tool). Falls back to returning None whenever the key is missing,
the search comes back empty, or the request fails for any reason - every
caller in sfx.py/bgm.py treats that as "use the synthesized version
instead," so a Freesound outage never breaks a video build.

License handling: CC0-licensed results are preferred (no attribution
needed). If none are available, an Attribution-licensed result is used
instead and its credit info is returned so the caller can record it -
see pipeline.py's ATTRIBUTION.txt output.
"""
from __future__ import annotations

from pathlib import Path

import requests

from .config import settings

_SEARCH_URL = "https://freesound.org/apiv2/search/text/"
_CC0_LICENSES = {
    "http://creativecommons.org/publicdomain/zero/1.0/",
    "https://creativecommons.org/publicdomain/zero/1.0/",
}


def is_cc0(license_url: str) -> bool:
    return license_url in _CC0_LICENSES


def search_and_download(
    query: str,
    out_path: Path,
    min_duration: float = 0.0,
    max_duration: float = 60.0,
) -> dict | None:
    """Search Freesound for ``query`` and download the best match's preview
    mp3 to ``out_path``. Returns credit metadata (name/username/license/url)
    on success, or None if unavailable/not found for any reason.
    """
    if not settings.freesound_api_key:
        return None

    try:
        resp = requests.get(
            _SEARCH_URL,
            params={
                "query": query,
                "token": settings.freesound_api_key,
                "fields": "id,name,username,license,previews,duration,url",
                "filter": f"duration:[{min_duration} TO {max_duration}]",
                "sort": "rating_desc",
                "page_size": 10,
            },
            timeout=20,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return None

        chosen = next((r for r in results if is_cc0(r.get("license", ""))), results[0])
        previews = chosen.get("previews", {})
        preview_url = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
        if not preview_url:
            return None

        audio_resp = requests.get(preview_url, timeout=30)
        audio_resp.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(audio_resp.content)

        return {
            "name": chosen["name"],
            "username": chosen["username"],
            "license": chosen["license"],
            "url": chosen.get("url", ""),
        }
    except Exception:
        return None
