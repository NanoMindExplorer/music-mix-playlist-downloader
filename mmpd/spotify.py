"""
Spotify parser wrapper — high-level API untuk parse URL Spotify.

Membungkus spotify_parser.py (yang masih standalone flat module) dengan
type hints dan error handling yang lebih baik.

Functions:
    parse_spotify_url_safe  — parse URL dengan try/except + logging
    search_youtube_for_track — bangun query ytsearch untuk satu track Spotify
"""

from __future__ import annotations

from typing import List, Optional

from mmpd.logger import get_logger
from mmpd.utils.matching import clean_search_query

_log = get_logger()


def parse_spotify_url_safe(url: str) -> List[str]:
    """
    Parse URL Spotify (track/playlist/album) → list of "Artist Title" strings.

    Wrapper aman untuk spotify_parser.parse_spotify_url(). Menambahkan:
    - Type hints
    - Logging jika gagal
    - Empty list fallback (bukan raise exception)

    Args:
        url: URL Spotify (mis. https://open.spotify.com/playlist/xxx)

    Returns:
        List of query strings siap untuk ytsearch ("Artist Title").
        Empty list jika gagal parse atau URL invalid.
    """
    try:
        from spotify_parser import parse_spotify_url
    except ImportError:
        _log.error("Module spotify_parser tidak ditemukan")
        return []

    if "open.spotify.com" not in url:
        _log.warning("URL bukan Spotify: %s", url[:80])
        return []

    try:
        results = parse_spotify_url(url)
        _log.info("Spotify parsed: %d tracks dari %s", len(results), url[:80])
        return results or []
    except Exception as e:
        _log.error("Spotify parse error untuk %s: %s", url[:80], e, exc_info=True)
        return []


def build_ytsearch_query(track_query: str, limit: int = 1) -> str:
    """
    Bangun query string ytsearch untuk yt-dlp.

    Args:
        track_query: String pencarian (mis. "Adele Hello")
        limit:       Jumlah hasil yang diinginkan (default 1)

    Returns:
        String format ytsearch{limit}:{query}
    """
    # Bersihkan query dari karakter aneh tapi preserve spasi
    clean = clean_search_query(track_query)
    if not clean:
        clean = track_query.strip()
    return f"ytsearch{limit}:{clean}"


def is_spotify_url(url: str) -> bool:
    """Cek apakah string adalah URL Spotify yang valid."""
    return "open.spotify.com" in url and url.strip().startswith("http")
