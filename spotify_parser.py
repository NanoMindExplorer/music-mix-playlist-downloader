"""
spotify_parser.py — DEPRECATED (Fase 4).

Module ini pakai scraping HTML `__NEXT_DATA__` dari open.spotify.com/embed
untuk parse URL Spotify. Rapuh: Spotify sering ubah struktur HTML.

Sejak Fase 2.3, pakai `mmpd.spotify_client.SpotifyClient` (official API
via spotipy) sebagai PRIMARY parser. Module ini tetap dipertahankan
sebagai FALLBACK kalau spotipy tidak terinstal atau credentials tidak ada.

Fase 4: tambah deprecation warning saat dipanggil.

Migration path:
    Lama: from spotify_parser import parse_spotify_url
    Baru: from mmpd.spotify import parse_spotify_url_v2  # return List[SpotifyTrack]

Backward compatibility:
    parse_spotify_url(url) tetap return List[str] — dipakai oleh
    mmpd.spotify.parse_spotify_url_safe() sebagai fallback.
"""

from __future__ import annotations

import warnings
import re
import json
import urllib.request


# Deprecation flag — supaya warning cuma muncul sekali per session
_DEPRECATION_WARNED = False


def _warn_deprecated() -> None:
    """Tampilkan DeprecationWarning (hanya sekali per session)."""
    global _DEPRECATION_WARNED
    if _DEPRECATION_WARNED:
        return
    _DEPRECATION_WARNED = True
    warnings.warn(
        "spotify_parser.parse_spotify_url() is deprecated since Fase 4. "
        "Use mmpd.spotify.parse_spotify_url_v2() instead (official Spotify API "
        "via spotipy). This legacy scraping fallback will be removed in v4.0.",
        DeprecationWarning,
        stacklevel=3,
    )


def parse_spotify_url(url):
    """
    Parse URL Spotify (track/playlist/album) via HTML scraping.

    DEPRECATED sejak Fase 4. Pakai mmpd.spotify.parse_spotify_url_v2().

    Args:
        url: URL Spotify (mis. https://open.spotify.com/playlist/xxx)

    Returns:
        List of "Artist Title" strings. Empty list jika gagal.
    """
    _warn_deprecated()

    # Support for open.spotify.com
    if "open.spotify.com" not in url:
        return []

    # Change /track/ or /playlist/ to embed URL
    embed_url = url.replace("open.spotify.com", "open.spotify.com/embed").split("?")[0]

    req = urllib.request.Request(embed_url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        html = urllib.request.urlopen(req).read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching Spotify: {e}")
        return []

    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not m:
        print("Could not find Spotify data.")
        return []

    try:
        data = json.loads(m.group(1))
        entity = data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})

        results = []
        # If it's a playlist or album
        if 'trackList' in entity:
            for item in entity['trackList']:
                if 'title' in item and 'subtitle' in item:
                    results.append(f"{item['title']} {item['subtitle']}")
        # If it's a single track
        elif 'title' in entity and 'subtitle' in entity:
            results.append(f"{entity['title']} {entity['subtitle']}")

        return results
    except Exception as e:
        print(f"Error parsing Spotify data: {e}")
        return []


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(parse_spotify_url(sys.argv[1]))
