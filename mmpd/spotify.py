"""
Spotify parser wrapper — fallback chain dengan Fase 2.3 modernization.

Fase 2.3 menambahkan:
    1. SpotifyClient (spotipy) sebagai PRIMARY parser — official API, akurat
    2. spotify_parser.py (legacy scraping) sebagai FALLBACK
    3. SpotifyTrack dataclass dengan ISRC untuk matching YouTube akurat

Backward compatibility:
    - parse_spotify_url_safe() tetap return List[str] (untuk caller lama)
    - parse_spotify_url_v2() baru — return List[SpotifyTrack] (untuk Fase 2.3)
"""

from __future__ import annotations

from typing import List, Optional, Union

from mmpd.logger import get_logger
from mmpd.utils.matching import clean_search_query

_log = get_logger()


# ============================================================================
# Backward-compat: parse_spotify_url_safe (tetap return List[str])
# ============================================================================

def parse_spotify_url_safe(url: str) -> List[str]:
    """
    Parse URL Spotify (track/playlist/album) → list of "Artist Title" strings.

    BACKWARD COMPAT: signature tetap sama, tetap return List[str].

    Fase 2.3 improvement:
        - Coba spotipy (official API) lebih dulu kalau tersedia
        - Fallback ke legacy scraping (spotify_parser.py) kalau spotipy tidak ada
        - Logging lebih detail

    Args:
        url: URL Spotify (mis. https://open.spotify.com/playlist/xxx)

    Returns:
        List of query strings siap untuk ytsearch ("Artist Title").
        Empty list jika gagal parse atau URL invalid.
    """
    if not is_spotify_url(url):
        _log.warning("URL bukan Spotify: %s", url[:80])
        return []

    # === Strategi 1: spotipy (official API) ===
    try:
        from mmpd.spotify_client import get_spotify_client
        client = get_spotify_client()
        if client.is_available:
            _log.info("Spotify: pakai spotipy (official API)")
            tracks = client.parse_url(url)
            if tracks:
                # SpotifyTrack → "Artist Title" string untuk backward compat
                queries = [t.to_ytsearch_query() for t in tracks]
                _log.info("Spotify parsed (spotipy): %d tracks dari %s", len(queries), url[:80])
                return queries
            _log.warning("Spotify: spotipy return empty, fallback ke legacy scraping")
    except Exception as e:
        _log.warning("Spotify: spotipy gagal (%s), fallback ke legacy scraping", e)

    # === Strategi 2: legacy scraping (spotify_parser.py) ===
    try:
        from spotify_parser import parse_spotify_url
    except ImportError:
        _log.error("Module spotify_parser tidak ditemukan")
        return []

    try:
        results = parse_spotify_url(url)
        _log.info("Spotify parsed (legacy scraping): %d tracks dari %s", len(results), url[:80])
        return results or []
    except Exception as e:
        _log.error("Spotify parse error untuk %s: %s", url[:80], e, exc_info=True)
        return []


# ============================================================================
# Fase 2.3: parse_spotify_url_v2 (return List[SpotifyTrack])
# ============================================================================

def parse_spotify_url_v2(url: str):
    """
    Parse URL Spotify → List[SpotifyTrack] (lebih kaya metadata, ada ISRC).

    Sama dengan parse_spotify_url_safe() tapi return SpotifyTrack yang punya:
        - title, artist, album
        - isrc (untuk YouTube matching akurat 99%+)
        - duration_ms (untuk duration verification)
        - spotify_url (untuk debugging)
        - popularity (untuk disambiguation)

    Returns:
        List[SpotifyTrack] kalau spotipy available, List[] kalau tidak.
        Fallback ke legacy: List[SpotifyTrack] dengan title+artist saja (no ISRC).
    """
    if not is_spotify_url(url):
        return []

    # === Strategi 1: spotipy (official API) ===
    try:
        from mmpd.spotify_client import get_spotify_client, SpotifyTrack
        client = get_spotify_client()
        if client.is_available:
            _log.info("Spotify v2: pakai spotipy (official API)")
            tracks = client.parse_url(url)
            if tracks:
                _log.info(
                    "Spotify v2 parsed (spotipy): %d tracks, %d with ISRC",
                    len(tracks),
                    sum(1 for t in tracks if t.isrc),
                )
                return tracks
    except Exception as e:
        _log.warning("Spotify v2: spotipy gagal (%s), fallback ke legacy", e)

    # === Strategi 2: legacy scraping + wrap ke SpotifyTrack ===
    try:
        from spotify_parser import parse_spotify_url
        from mmpd.spotify_client import SpotifyTrack
        raw_results = parse_spotify_url(url)
        if not raw_results:
            return []

        # Convert raw "Artist Title" strings → SpotifyTrack (no ISRC)
        tracks: List[SpotifyTrack] = []
        for query in raw_results:
            # Heuristik: pisahkan "Artist Title" — split di spasi pertama
            # (tidak akurat, tapi better than nothing)
            parts = query.split(" ", 1)
            if len(parts) == 2:
                artist, title = parts
            else:
                artist, title = "", query

            tracks.append(SpotifyTrack(
                title=title,
                artist=artist,
            ))

        _log.info(
            "Spotify v2 parsed (legacy): %d tracks (tanpa ISRC)",
            len(tracks),
        )
        return tracks
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
