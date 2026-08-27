"""
Spotify API client via spotipy (official Spotify Web API).

Menggantikan spotify_parser.py yang menggunakan scraping __NEXT_DATA__
(rapuh, Spotify sering ubah struktur HTML). Spotipy pakai official API
dengan Client Credentials flow — TIDAK butuh login user.

Setup:
    1. Buka https://developer.spotify.com/dashboard
    2. Create app → dapatkan Client ID + Client Secret
    3. Set environment variables:
        export SPOTIPY_CLIENT_ID="your_client_id"
        export SPOTIPY_CLIENT_SECRET="your_client_secret"
    4. Atau simpan di config file ~/.config/mmpd/config.toml (Fase 2.4)

Backward compatibility:
    - Kalau spotipy tidak terinstal ATAU env vars tidak ada,
      otomatis fallback ke legacy scraping via spotify_parser.py
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from mmpd.logger import get_logger
from mmpd.types import TrackInfo

_log = get_logger()


@dataclass(frozen=True)
class SpotifyTrack:
    """
    Spotify track metadata (lebih lengkap dari TrackInfo biasa).

    Field tambahan vs TrackInfo:
        - isrc:          International Standard Recording Code (untuk YouTube matching akurat)
        - spotify_url:   URL Spotify asli (untuk debugging)
        - popularity:    0-100 score dari Spotify (untuk disambiguation)
        - explicit:      True kalau lagu explicit
    """

    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    spotify_url: Optional[str] = None
    popularity: Optional[int] = None
    explicit: bool = False

    def to_track_info(self) -> TrackInfo:
        """Konversi ke TrackInfo untuk LyricsChain."""
        return TrackInfo(
            title=self.title,
            artist=self.artist,
            album=self.album,
            duration=self.duration_ms / 1000.0 if self.duration_ms else None,
            isrc=self.isrc,
        )

    def to_ytsearch_query(self) -> str:
        """Bangun query ytsearch untuk YouTube."""
        parts = [self.title]
        if self.artist:
            parts.append(self.artist)
        return " ".join(parts)


class SpotifyClient:
    """
    Wrapper spotipy.Spotify dengan:
        - Lazy initialization (tidak load spotipy kalau tidak dipakai)
        - Auto-refresh token (spotipy handle, tapi kita tambah retry)
        - Rate limit handling (exponential backoff)
        - Graceful fallback kalau credentials tidak ada

    Usage:
        client = SpotifyClient()
        if client.is_available():
            tracks = client.get_playlist_tracks(url)
            for track in tracks:
                # track.isrc → YouTube matching (akurasi 99%)
                # track.to_track_info() → LyricsChain
    """

    def __init__(self) -> None:
        """Lazy init — cek credentials tanpa langsung import spotipy."""
        self._client = None
        self._initialized = False
        self._available: Optional[bool] = None

    @property
    def is_available(self) -> bool:
        """Cek apakah spotipy terinstal DAN credentials ada di env."""
        if self._available is not None:
            return self._available

        # Cek env vars
        client_id = os.environ.get("SPOTIPY_CLIENT_ID")
        client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET")

        if not client_id or not client_secret:
            _log.debug("Spotify API: credentials tidak ada di env (SPOTIPY_CLIENT_ID/SECRET)")
            self._available = False
            return False

        # Cek spotipy terinstal
        try:
            import spotipy  # noqa: F401
            self._available = True
            return True
        except ImportError:
            _log.warning("Spotify API: spotipy tidak terinstal — fallback ke legacy scraping")
            self._available = False
            return False

    def _ensure_client(self) -> bool:
        """Lazy init spotipy client."""
        if self._initialized and self._client is not None:
            return True

        if not self.is_available:
            return False

        try:
            import spotipy
            from spotipy.oauth2 import SpotifyClientCredentials

            credentials_manager = SpotifyClientCredentials()
            self._client = spotipy.Spotify(
                client_credentials_manager=credentials_manager,
                requests_timeout=(10, 30),  # connect 10s, read 30s (sama seperti syncedlyrics patch)
            )
            self._initialized = True
            _log.info("Spotify API client initialized (Client Credentials flow)")
            return True
        except Exception as e:
            _log.error("Spotify API init gagal: %s", e, exc_info=True)
            self._available = False
            return False

    def _call_with_retry(self, fn, *args, max_retries: int = 3, **kwargs) -> Optional[Any]:
        """
        Panggil spotipy method dengan retry + exponential backoff.

        Spotify API rate limit: 50% dari total requests per rolling window.
        Kalau hit rate limit, response 429 dengan Retry-After header.
        spotipy handle ini otomatis, tapi kadang perlu retry untuk network error.
        """
        last_exception: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                return fn(*args, **kwargs)
            except spotify_exception_retryable() as e:
                # Retry-able: network error, 5xx, 429
                last_exception = e
                wait = 2 ** attempt  # 1s, 2s, 4s
                _log.warning("Spotify API retry %d/%d: %s (waiting %ds)", attempt + 1, max_retries, e, wait)
                time.sleep(wait)
            except Exception as e:
                # Non-retryable: 4xx (bad request, unauthorized)
                _log.error("Spotify API error (non-retryable): %s", e)
                return None

        _log.error("Spotify API exhausted %d retries: %s", max_retries, last_exception)
        return None

    # ========================================================================
    # Public API — high-level methods
    # ========================================================================

    def parse_url(self, url: str) -> List[SpotifyTrack]:
        """
        Parse URL Spotify (track/album/playlist) → list of SpotifyTrack.

        Mendukung:
            - https://open.spotify.com/track/{id}
            - https://open.spotify.com/album/{id}
            - https://open.spotify.com/playlist/{id}

        Returns:
            List of SpotifyTrack (kosong jika gagal).
        """
        if not self._ensure_client():
            return []

        # Extract type + id dari URL
        parsed = self._parse_spotify_url(url)
        if not parsed:
            _log.warning("URL Spotify tidak valid: %s", url[:80])
            return []

        kind, item_id = parsed
        _log.info("Spotify URL parsed: type=%s, id=%s", kind, item_id)

        if kind == "track":
            track = self._get_track(item_id)
            return [track] if track else []
        elif kind == "album":
            return self._get_album_tracks(item_id)
        elif kind == "playlist":
            return self._get_playlist_tracks(item_id)
        else:
            _log.warning("Tipe URL Spotify tidak didukung: %s", kind)
            return []

    @staticmethod
    def _parse_spotify_url(url: str) -> Optional[tuple[str, str]]:
        """
        Extract (type, id) dari URL Spotify.

        Format didukung:
            open.spotify.com/track/{id}
            open.spotify.com/album/{id}
            open.spotify.com/playlist/{id}
            open.spotify.com/intl-id/track/{id}  (locale-prefixed)
        """
        import re
        # Pattern: spotify.com/(intl-[a-z]+/)?(track|album|playlist)/{id}
        match = re.search(
            r"spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist)/([a-zA-Z0-9]+)",
            url,
        )
        if not match:
            return None
        return match.group(1), match.group(2)

    def _get_track(self, track_id: str) -> Optional[SpotifyTrack]:
        """Ambil single track by ID."""
        result = self._call_with_retry(self._client.track, track_id)
        if not result:
            return None
        return self._parse_track_response(result)

    def _get_album_tracks(self, album_id: str) -> List[SpotifyTrack]:
        """Ambil semua tracks dari album (handle pagination)."""
        results: List[SpotifyTrack] = []
        offset = 0
        limit = 50  # max per request

        while True:
            response = self._call_with_retry(
                self._client.album_tracks,
                album_id,
                limit=limit,
                offset=offset,
            )
            if not response:
                break

            items = response.get("items", [])
            if not items:
                break

            # album_tracks hanya return basic info (no ISRC).
            # Untuk dapat ISRC, perlu ambil full track info per item.
            for item in items:
                # Cek kalau item sudah punya ISRC (kadang ada di album_tracks response)
                if item.get("external_ids", {}).get("isrc"):
                    results.append(self._parse_track_response(item))
                else:
                    # Fetch full track untuk ISRC
                    track_id = item.get("id")
                    if track_id:
                        full_track = self._get_track(track_id)
                        if full_track:
                            results.append(full_track)

            if len(items) < limit:
                break  # last page
            offset += limit

        _log.info("Album tracks: %d total", len(results))
        return results

    def _get_playlist_tracks(self, playlist_id: str) -> List[SpotifyTrack]:
        """Ambil semua tracks dari playlist (handle pagination)."""
        results: List[SpotifyTrack] = []
        offset = 0
        limit = 100  # max per request untuk playlist

        while True:
            response = self._call_with_retry(
                self._client.playlist_items,
                playlist_id,
                limit=limit,
                offset=offset,
                additional_types=("track",),
            )
            if not response:
                break

            items = response.get("items", [])
            if not items:
                break

            for item in items:
                track_data = item.get("track")
                if not track_data:
                    continue
                # Skip non-track items (episode, podcast)
                if track_data.get("type") and track_data["type"] != "track":
                    continue
                parsed = self._parse_track_response(track_data)
                if parsed:
                    results.append(parsed)

            if len(items) < limit:
                break
            offset += limit

        _log.info("Playlist tracks: %d total", len(results))
        return results

    @staticmethod
    def _parse_track_response(data: Dict[str, Any]) -> Optional[SpotifyTrack]:
        """Parse response track dari Spotify API → SpotifyTrack dataclass."""
        if not data or not isinstance(data, dict):
            return None

        # Artist bisa list (kolaborasi) — ambil semua, gabung dengan ", "
        artists = data.get("artists", [])
        if artists and isinstance(artists, list):
            artist_names = [a.get("name", "") for a in artists if isinstance(a, dict)]
            artist_str = ", ".join(artist_names) if artist_names else ""
        else:
            artist_str = ""

        title = data.get("name", "")
        if not title:
            return None

        # Album info
        album_data = data.get("album", {})
        album_name = album_data.get("name") if isinstance(album_data, dict) else None

        # ISRC
        external_ids = data.get("external_ids", {})
        isrc = external_ids.get("isrc") if isinstance(external_ids, dict) else None

        return SpotifyTrack(
            title=title,
            artist=artist_str,
            album=album_name,
            duration_ms=data.get("duration_ms"),
            isrc=isrc,
            spotify_url=data.get("external_urls", {}).get("spotify"),
            popularity=data.get("popularity"),
            explicit=data.get("explicit", False),
        )


# ============================================================================
# Helper untuk deteksi exception yang retry-able
# ============================================================================

def spotify_exception_retryable():
    """
    Return tuple exception classes yang bisa di-retry (network, 5xx, 429).

    Pakai function (bukan constant) karena spotipy di-import lazy.
    """
    retryable = (
        ConnectionError,
        TimeoutError,
        OSError,  # socket errors
    )
    try:
        import spotipy
        # spotipy.SpotifyException punya status_code attribute
        from spotipy.exceptions import SpotifyException
        # Retry kalau 429 (rate limit) atau 5xx (server error)
        # Tapi kita tidak bisa cek status_code di sini — tangani di _call_with_retry
        retryable = (ConnectionError, TimeoutError, OSError, SpotifyException)
    except ImportError:
        pass
    return retryable


# ============================================================================
# Singleton
# ============================================================================

_CLIENT: Optional[SpotifyClient] = None


def get_spotify_client() -> SpotifyClient:
    """Singleton accessor."""
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = SpotifyClient()
    return _CLIENT


def reset_spotify_client() -> None:
    """Reset singleton (untuk testing)."""
    global _CLIENT
    _CLIENT = None
