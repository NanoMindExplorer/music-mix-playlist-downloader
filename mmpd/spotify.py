"""
Spotify parser — official API via spotipy (Fase 5: legacy scraping removed).

Sejak Fase 5, module ini HANYA pakai spotipy (official Spotify Web API).
Legacy scraping (spotify_parser.py) sudah dihapus.

Functions:
    parse_spotify_url_safe  — return List[str] (backward compat untuk caller lama)
    parse_spotify_url_v2     — return List[SpotifyTrack] (recommended, ada ISRC)
    build_ytsearch_query    — bangun ytsearch string
    is_spotify_url          — validator URL
    spotipy_available       — cek spotipy + credentials

Setup credentials:
    export SPOTIPY_CLIENT_ID="your_client_id"
    export SPOTIPY_CLIENT_SECRET="your_client_secret"

Tanpa credentials: parse return empty list. User harus setup credentials
untuk pakai Mode 4 (Spotify download).
"""

from __future__ import annotations

from typing import List

from mmpd.logger import get_logger
from mmpd.utils.matching import clean_search_query

_log = get_logger()


# ============================================================================
# parse_spotify_url_safe (return List[str], backward compat)
# ============================================================================

def parse_spotify_url_safe(url: str) -> List[str]:
    """
    Parse URL Spotify (track/playlist/album) → list of "Artist Title" strings.

    BACKWARD COMPAT: signature tetap sama, return List[str].

    Fase 5: HANYA pakai spotipy (official API). Legacy scraping dihapus.
    Kalau spotipy tidak available atau credentials tidak ada, return [].

    Args:
        url: URL Spotify (mis. https://open.spotify.com/playlist/xxx)

    Returns:
        List of query strings siap untuk ytsearch ("Artist Title").
        Empty list jika gagal atau credentials tidak ada.
    """
    if not is_spotify_url(url):
        _log.warning("URL bukan Spotify: %s", url[:80])
        return []

    try:
        from mmpd.spotify_client import get_spotify_client
        client = get_spotify_client()
        
        _log.info("Spotify: Parsing URL")
        tracks = client.parse_url(url)
        if tracks:
            queries = [t.to_ytsearch_query() for t in tracks]
            _log.info("Spotify parsed: %d tracks dari %s", len(queries), url[:80])
            return queries
        else:
            if client.last_error:
                _log.error("Spotify gagal: %s", client.last_error)
            else:
                _log.warning("Spotify: return empty (URL invalid atau playlist kosong)")
            return []
    except Exception as e:
        _log.error("Spotify parse error untuk %s: %s", url[:80], e, exc_info=True)
        return []


# ============================================================================
# parse_spotify_url_v2 (return List[SpotifyTrack], recommended)
# ============================================================================

def parse_spotify_url_v2(url: str):
    """
    Parse URL Spotify → List[SpotifyTrack] (lebih kaya metadata, ada ISRC).

    SpotifyTrack punya:
        - title, artist, album
        - isrc (untuk YouTube matching akurat 99%+)
        - duration_ms (untuk duration verification)
        - spotify_url (untuk debugging)
        - popularity (untuk disambiguation)

    Returns:
        List[SpotifyTrack]. Empty list jika spotipy tidak available atau
        credentials tidak ada.
    """
    if not is_spotify_url(url):
        return []

    try:
        from mmpd.spotify_client import get_spotify_client, SpotifyTrack
        client = get_spotify_client()
        
        _log.info("Spotify v2: Parsing URL")
        tracks = client.parse_url(url)
        if tracks:
            _log.info(
                "Spotify v2 parsed: %d tracks, %d with ISRC",
                len(tracks),
                sum(1 for t in tracks if getattr(t, 'isrc', None)),
            )
            return tracks
        else:
            if client.last_error:
                _log.error("Spotify v2 gagal: %s", client.last_error)
            else:
                _log.warning("Spotify v2: return empty")
            return []
    except Exception as e:
        _log.error("Spotify v2 parse error: %s", e, exc_info=True)
        return []


# ============================================================================
# Helpers
# ============================================================================

def build_ytsearch_query(track_query: str, limit: int = 1) -> str:
    """
    Bangun query string ytsearch untuk yt-dlp.

    Args:
        track_query: String pencarian (mis. "Adele Hello")
        limit:       Jumlah hasil yang diinginkan (default 1)

    Returns:
        String format ytsearch{limit}:{query}
    """
    clean = clean_search_query(track_query)
    if not clean:
        clean = track_query.strip()
    # Fix instrumental: Gunakan exclusion filter yt-dlp / youtube
    clean = f'{clean} -instrumental -karaoke official audio'
    return f"ytsearch{limit}:{clean}"


def is_spotify_url(url: str) -> bool:
    """Cek apakah string adalah URL Spotify yang valid."""
    return "open.spotify.com" in url and url.strip().startswith("http")


def spotipy_available() -> bool:
    """Cek apakah spotipy available (terinstal + credentials ada)."""
    try:
        from mmpd.spotify_client import get_spotify_client
        return get_spotify_client().is_available
    except Exception:
        return False
