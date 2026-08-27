"""
Lyrics Providers: implementasi LyricsProvider protocol + fallback chain.

Providers (urutan priority):
    1. LrclibProvider       (priority=0) — LRCLIB API, gratis, no-auth, database terbesar
    2. SyncedLyricsProvider (priority=10) — syncedlyrics library (current default)

Fallback Chain:
    LyricsChain.search(track) mencoba provider sesuai priority, urut ascending.
    Return hasil pertama yang sukses. Jika semua gagal, return None.

Penambahan provider baru:
    1. Implement LyricsProvider protocol
    2. Tambah ke LyricsChain default chain di build_default_chain()
    3. Tidak perlu modif caller code (downloader.py)
"""

from __future__ import annotations

import time
from typing import List, Optional

from mmpd.logger import get_logger
from mmpd.types import LyricsProvider, LyricsResult, TrackInfo


# ============================================================================
# Provider 1: LRCLIB (https://lrclib.net) — FREE, NO AUTH, LARGEST DB
# ============================================================================

class LrclibProvider:
    """
    Provider LRCLIB — database lirik sinkron terbesar, gratis, tanpa auth.

    API docs: https://lrclib.net/docs

    Endpoint:
        GET /api/get    — exact match by track_name + artist_name (+ optional album, duration)
        GET /api/search — fuzzy search by query string

    Keunggulan:
        - Free forever, no API key
        - Database > 1 juta synced lyrics
        - Mendukung search by ISRC (paling akurat)
        - Rate limit generous (100 req/min untuk anonymous)
    """

    name = "lrclib"
    priority = 0  # highest priority

    BASE_URL = "https://lrclib.net/api"
    REQUEST_TIMEOUT = (10, 30)  # (connect, read) detik

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        """Cari lirik di LRCLIB. Return None jika tidak ditemukan."""
        log = get_logger()
        log.debug("LRCLIB search: query='%s', isrc=%s", track.search_query(), track.isrc)

        try:
            import requests
        except ImportError:
            log.warning("LRCLIB: modul 'requests' belum terinstal, skip provider")
            return None

        # === Strategi 1: Search by ISRC (paling akurat) ===
        if track.isrc:
            result = self._search_by_isrc(requests, track.isrc)
            if result is not None:
                log.info("LRCLIB: match by ISRC for '%s'", track.title)
                return result

        # === Strategi 2: Exact match by track_name + artist + duration ===
        if track.artist and track.duration:
            result = self._get_exact_match(requests, track)
            if result is not None:
                log.info("LRCLIB: exact match for '%s' by '%s'", track.title, track.artist)
                return result

        # === Strategi 3: Fuzzy search ===
        result = self._fuzzy_search(requests, track)
        if result is not None:
            log.info("LRCLIB: fuzzy match for '%s'", track.title)
            return result

        log.debug("LRCLIB: no match for '%s'", track.title)
        return None

    def _search_by_isrc(self, requests_module, isrc: str) -> Optional[LyricsResult]:
        """Search by ISRC code (paling akurat)."""
        try:
            url = f"{self.BASE_URL}/get?isrc={isrc}"
            res = requests_module.get(url, timeout=self.REQUEST_TIMEOUT, headers={"User-Agent": "mmpd/3.1"})
            if res.status_code == 404:
                return None
            res.raise_for_status()
            data = res.json()
            return self._parse_lrclib_response(data)
        except Exception:
            return None

    def _get_exact_match(self, requests_module, track: TrackInfo) -> Optional[LyricsResult]:
        """Exact match by track_name + artist_name + duration."""
        try:
            params = {
                "track_name": track.title,
                "artist_name": track.artist or "",
            }
            if track.duration:
                # LRCLIB expect duration in ms, akurat ke detik
                params["duration"] = str(int(track.duration))

            url = f"{self.BASE_URL}/get"
            res = requests_module.get(
                url,
                params=params,
                timeout=self.REQUEST_TIMEOUT,
                headers={"User-Agent": "mmpd/3.1"},
            )
            if res.status_code == 404:
                return None
            res.raise_for_status()
            data = res.json()
            return self._parse_lrclib_response(data)
        except Exception:
            return None

    def _fuzzy_search(self, requests_module, track: TrackInfo) -> Optional[LyricsResult]:
        """Fuzzy search by query string."""
        try:
            from urllib.parse import quote
            query = track.clean_search_query()
            if not query:
                return None

            url = f"{self.BASE_URL}/search?q={quote(query)}"
            res = requests_module.get(
                url,
                timeout=self.REQUEST_TIMEOUT,
                headers={"User-Agent": "mmpd/3.1"},
            )
            res.raise_for_status()
            items = res.json()
            if not items:
                return None

            # Ambil hasil pertama (LRCLIB sudah sort by relevance)
            return self._parse_lrclib_response(items[0])
        except Exception:
            return None

    @staticmethod
    def _parse_lrclib_response(data: dict) -> Optional[LyricsResult]:
        """Parse response dari LRCLIB API ke LyricsResult."""
        if not data:
            return None
        return LyricsResult(
            synced_lyrics=data.get("syncedLyrics") or "",
            plain_lyrics=data.get("plainLyrics"),
            provider="lrclib",
            track_name=data.get("trackName"),
            artist_name=data.get("artistName"),
            duration_ms=data.get("duration"),
        )


# ============================================================================
# Provider 2: syncedlyrics (wrapper library lama, tetap dipertahankan)
# ============================================================================

class SyncedLyricsProvider:
    """
    Wrapper untuk library `syncedlyrics` (yang dipakai sejak Fase 0).

    syncedlyrics meng-agregasi multi-sumber: Musixmatch, NetEase, Megalobiz, etc.
    Tidak butuh API key. Masih relevan sebagai fallback kalau LRCLIB tidak punya.

    Patch Fase 1 sudah monkey-patch timeout default ke (10, 30) detik.
    """

    name = "syncedlyrics"
    priority = 10

    def __init__(self) -> None:
        """Lazy init syncedlyrics, dengan patch timeout dari Fase 1."""
        self._initialized = False
        self._search_fn = None

    def _ensure_initialized(self) -> bool:
        """Lazy import + apply timeout patch."""
        if self._initialized:
            return True

        log = get_logger()
        try:
            import syncedlyrics
            # Patch bawaan syncedlyrics yang membatasi timeout koneksi menjadi 2 detik
            # (terlalu singkat untuk Termux/koneksi lambat). Sama seperti Fase 1 patch.
            try:
                from syncedlyrics.providers.base import TimeoutSession

                def custom_request(self, method, url, **kwargs):
                    kwargs.setdefault("timeout", (10, 30))
                    return super(TimeoutSession, self).request(method, url, **kwargs)

                TimeoutSession.request = custom_request
            except Exception as e:
                log.debug("syncedlyrics timeout patch failed (non-critical): %s", e)

            self._search_fn = syncedlyrics.search
            self._initialized = True
            return True
        except ImportError:
            log.warning("syncedlyrics: modul belum terinstal, skip provider")
            return False

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        """Cari lirik via syncedlyrics. Return None jika tidak ditemukan."""
        log = get_logger()
        if not self._ensure_initialized():
            return None

        # Coba pakai clean query dulu (lebih akurat)
        clean_query = track.clean_search_query()
        log.debug("syncedlyrics search: query='%s'", clean_query)

        try:
            lrc_text = self._search_fn(clean_query)
            if not lrc_text:
                # Fallback: coba raw query
                raw_query = track.search_query()
                if raw_query != clean_query:
                    log.debug("syncedlyrics retry with raw query: '%s'", raw_query)
                    lrc_text = self._search_fn(raw_query)

            if not lrc_text:
                log.debug("syncedlyrics: no match for '%s'", track.title)
                return None

            return LyricsResult(
                synced_lyrics=lrc_text,
                plain_lyrics=None,
                provider="syncedlyrics",
                track_name=track.title,
                artist_name=track.artist,
            )
        except Exception as e:
            log.warning("syncedlyrics: error for '%s': %s", track.title, e)
            return None


# ============================================================================
# Fallback Chain — coba provider satu per satu sampai dapat hasil
# ============================================================================

class LyricsChain:
    """
    Fallback chain: coba provider sesuai urutan priority.

    Usage:
        chain = LyricsChain([LrclibProvider(), SyncedLyricsProvider()])
        result = chain.search(track)
        if result:
            print(f"Found via {result.provider}")
    """

    def __init__(self, providers: List[LyricsProvider]) -> None:
        # Sort by priority ascending (0 = highest)
        self._providers = sorted(providers, key=lambda p: p.priority)
        self._log = get_logger()

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        """
        Cari lirik di semua provider secara berurutan.
        Return hasil pertama yang sukses, atau None jika semua gagal.

        Fase 4: cek lyrics cache (SQLite) sebelum panggil provider.
        Cache hit → skip API call, return cached result.
        Cache miss → panggil provider, cache hasilnya (TTL 30 hari).
        """
        self._log.debug(
            "LyricsChain.search: trying %d providers for '%s'",
            len(self._providers),
            track.title,
        )

        # === Fase 4: Cek lyrics cache dulu ===
        try:
            from mmpd.cache import get_lyrics_cache, set_lyrics_cache
            cached = get_lyrics_cache(
                track_title=track.title,
                artist=track.artist,
                isrc=track.isrc,
            )
            if cached is not None:
                synced, plain, provider_name = cached
                self._log.info("Lyrics cache HIT: %s (provider=%s)", track.title, provider_name)
                return LyricsResult(
                    synced_lyrics=synced or "",
                    plain_lyrics=plain,
                    provider=f"{provider_name} (cached)",
                    track_name=track.title,
                    artist_name=track.artist,
                )
        except ImportError:
            self._log.debug("mmpd.cache tidak tersedia, skip lyrics cache")
        except Exception as e:
            self._log.warning("Lyrics cache read error: %s", e)

        # === Cache miss: panggil provider ===
        for provider in self._providers:
            provider_name = getattr(provider, "name", provider.__class__.__name__)
            self._log.debug("LyricsChain: trying provider '%s'", provider_name)

            try:
                t0 = time.monotonic()
                result = provider.search(track)
                elapsed = time.monotonic() - t0

                if result is not None and result.best_lyrics:
                    self._log.info(
                        "LyricsChain: FOUND via '%s' in %.2fs (synced=%s)",
                        provider_name,
                        elapsed,
                        result.has_synced,
                    )
                    # Fase 4: cache hasilnya
                    try:
                        from mmpd.cache import set_lyrics_cache
                        set_lyrics_cache(
                            track_title=track.title,
                            synced_lyrics=result.synced_lyrics,
                            plain_lyrics=result.plain_lyrics,
                            artist=track.artist,
                            isrc=track.isrc,
                            provider=provider_name,
                        )
                    except Exception as e:
                        self._log.warning("Lyrics cache write error: %s", e)
                    return result
                else:
                    self._log.debug(
                        "LyricsChain: provider '%s' returned no result (%.2fs)",
                        provider_name,
                        elapsed,
                    )
            except Exception as e:
                # Jangan biarkan satu provider crash seluruh chain
                self._log.warning(
                    "LyricsChain: provider '%s' raised exception: %s",
                    provider_name,
                    e,
                )
                continue

        self._log.info("LyricsChain: no provider returned lyrics for '%s'", track.title)
        return None


def build_default_chain() -> LyricsChain:
    """
    Build default lyrics chain: LRCLIB → syncedlyrics.

    Future providers (Musixmatch, NetEase direct, YoutubeCC) bisa ditambahkan
    di sini tanpa modif caller code.
    """
    return LyricsChain([
        LrclibProvider(),
        SyncedLyricsProvider(),
    ])
