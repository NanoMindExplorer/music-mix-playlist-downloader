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
# P0-fix: Circuit breaker per-provider (module-level, satu state untuk semua)
# ============================================================================
# Versi lama mendefinisikan `_PROVIDER_FAILS` sebagai class attribute di dalam
# SyncedLyricsProvider tapi mengaksesnya via `global` — assignment masuk ke
# module scope, pembacaan dari class scope → dua dict berbeda + state bocor
# antar test. Sekarang: satu module-level dict + helper eksplisit.

_PROVIDER_FAILS: dict = {}
_PROVIDER_FAIL_THRESHOLD = 3

# Fase L: wall-clock timeout untuk provider yang bisa hang (khususnya NetEase
# via syncedlyrics — endpoint-nya lambat dan patch timeout requests tidak
# menutup kasus server yang menerima koneksi tapi tidak pernah menjawab).
# Executor dibuat sekali dan TIDAK pernah di-shutdown (thread daemon-leak
# terkontrol, max 1 executor per process) supaya future yang timeout tidak
# memblokir shutdown handler.
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from concurrent.futures import TimeoutError as _FutureTimeoutError  # noqa: E402

_SEARCH_EXECUTOR: ThreadPoolExecutor | None = None
_PROVIDER_CALL_TIMEOUT = 30.0  # detik per panggilan provider


def _get_search_executor() -> ThreadPoolExecutor:
    global _SEARCH_EXECUTOR
    if _SEARCH_EXECUTOR is None:
        _SEARCH_EXECUTOR = ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="mmpd-provider"
        )
    return _SEARCH_EXECUTOR


def call_with_timeout(fn, *args, timeout: float = _PROVIDER_CALL_TIMEOUT, **kwargs):
    """Jalankan fn(*args, **kwargs) dengan batas waktu wall-clock.

    Kalau lewat batas waktu, raise TimeoutError. Thread yang hung dibiarkan
    jalan di background (tidak bisa dipaksa dibunuh di Python) tapi caller
    sudah bebas melanjutkan ke provider berikutnya.
    """
    future = _get_search_executor().submit(fn, *args, **kwargs)
    try:
        return future.result(timeout=timeout)
    except _FutureTimeoutError as e:
        raise TimeoutError(
            f"provider call exceeded {timeout:.0f}s wall-clock limit"
        ) from e


# Fase R: HTTP GET dengan retry + exponential backoff untuk 429/5xx.
# Semua provider requests-based memakai helper ini supaya rate-limit YouTube
# Music / Musixmatch tidak langsung mematikan seluruh chain.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_BACKOFF_BASE = 1.5  # detik; total tunggu maks ~1.5+3+4.5 ≈ 9 detik


def request_with_backoff(requests_module, url: str, **kwargs):
    """HTTP GET dengan retry eksponensial untuk status 429/5xx.

    Args:
        requests_module: modul requests (injectable untuk testing)
        url: URL lengkap
        **kwargs: diteruskan ke requests.get (timeout, params, headers, ...)

    Returns:
        Response object (status bisa saja non-2xx final — caller cek sendiri)
    """
    kwargs.setdefault("timeout", (10, 30))
    last_exc: Optional[Exception] = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            res = requests_module.get(url, **kwargs)
            if res.status_code not in _RETRYABLE_STATUS:
                return res
            get_logger().debug(
                "HTTP %d untuk %s (attempt %d/%d) — backoff %.1fs",
                res.status_code, url[:80], attempt + 1, _MAX_RETRIES + 1,
                _BACKOFF_BASE * (attempt + 1),
            )
        except Exception as e:  # network error (timeout, DNS, dsb)
            last_exc = e
            res = None
        if attempt < _MAX_RETRIES:
            time.sleep(_BACKOFF_BASE * (attempt + 1))
    if res is not None:
        return res  # status final setelah retry habis
    raise last_exc if last_exc else RuntimeError(f"request gagal: {url[:80]}")


def provider_is_tripped(name: str) -> bool:
    """True jika provider sudah gagal >= threshold kali berturut-turut (skip sisa sesi)."""
    return _PROVIDER_FAILS.get(name, 0) >= _PROVIDER_FAIL_THRESHOLD


def record_provider_fail(name: str) -> None:
    """Catat satu kegagalan provider (increment breaker)."""
    _PROVIDER_FAILS[name] = _PROVIDER_FAILS.get(name, 0) + 1


def record_provider_success(name: str) -> None:
    """Reset breaker provider setelah sukses."""
    _PROVIDER_FAILS[name] = 0


def reset_provider_breakers() -> None:
    """Reset semua breaker (untuk testing / awal sesi baru)."""
    _PROVIDER_FAILS.clear()


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
            res = request_with_backoff(
                requests_module, url, headers={"User-Agent": f"mmpd/{_mmpd_version()}"}
            )
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
            res = request_with_backoff(
                requests_module,
                url,
                params=params,
                headers={"User-Agent": f"mmpd/{_mmpd_version()}"},
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
            res = request_with_backoff(
                requests_module,
                url,
                headers={"User-Agent": f"mmpd/{_mmpd_version()}"},
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
# Provider 2: Musixmatch Native (Bypass syncedlyrics)
# ============================================================================

class MusixmatchProvider:
    """
    Native Musixmatch Provider menggunakan Desktop API.
    Lebih stabil daripada wrapper syncedlyrics karena kita handle
    token generation dan macro.subtitles.get secara langsung,
    dan langsung bypass limitasi.
    """

    name = "musixmatch_native"
    priority = 5

    BASE_URL = "https://apic-desktop.musixmatch.com/ws/1.1"
    APP_ID = "web-desktop-app-v1.0"
    REQUEST_TIMEOUT = (10, 30)

    def __init__(self) -> None:
        self._user_token = None
        self._token_time = 0

    def _get_token(self, requests_module) -> Optional[str]:
        import time
        # Cache token for 10 minutes
        if self._user_token and (time.time() - self._token_time) < 600:
            return self._user_token

        try:
            url = f"{self.BASE_URL}/token.get?app_id={self.APP_ID}"
            res = request_with_backoff(
                requests_module, url, headers={"User-Agent": "Mozilla/5.0"}
            )
            res.raise_for_status()
            data = res.json()
            token = data.get("message", {}).get("body", {}).get("user_token")
            if token:
                self._user_token = token
                self._token_time = time.time()
                return token
        except Exception as e:
            get_logger().warning("Musixmatch token generation failed: %s", e)
        return None

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        log = get_logger()
        try:
            import requests
        except ImportError:
            return None

        token = self._get_token(requests)
        if not token:
            return None

        # Build query
        params = {
            "format": "json",
            "app_id": self.APP_ID,
            "usertoken": token,
        }
        
        if track.isrc:
            params["track_isrc"] = track.isrc
        else:
            params["q_track"] = track.title
            if track.artist:
                params["q_artist"] = track.artist

        log.debug("Musixmatch search: query='%s', isrc=%s", track.search_query(), track.isrc)

        try:
            url = f"{self.BASE_URL}/macro.subtitles.get"
            # Fase R: pakai backoff untuk 429/5xx (Musixmatch rate-limit agresif)
            res = request_with_backoff(
                requests, url, params=params,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            res.raise_for_status()
            data = res.json()

            macro_calls = data.get("message", {}).get("body", {}).get("macro_calls", {})
            subtitles_list = macro_calls.get("track.subtitles.get", {}).get("message", {}).get("body", {}).get("subtitle_list", [])
            
            if not subtitles_list:
                log.debug("Musixmatch: no subtitles found for '%s'", track.title)
                return None
                
            synced_lyrics = subtitles_list[0].get("subtitle", {}).get("subtitle_body", "")
            if not synced_lyrics:
                return None

            # Get track metadata
            track_meta = macro_calls.get("matcher.track.get", {}).get("message", {}).get("body", {}).get("track", {})
            track_name = track_meta.get("track_name", track.title)
            artist_name = track_meta.get("artist_name", track.artist)

            log.info("Musixmatch: match for '%s'", track_name)
            return LyricsResult(
                synced_lyrics=synced_lyrics,
                plain_lyrics=None,
                provider="musixmatch",
                track_name=track_name,
                artist_name=artist_name,
            )

        except Exception as e:
            log.warning("Musixmatch API failed for '%s': %s", track.title, e)
            return None

# ============================================================================
# Provider 3: syncedlyrics (wrapper library lama, tetap dipertahankan)
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

    _PROVIDER_FAILS = {}  # deprecated alias (tidak dipakai lagi) — lihat module-level breaker

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        """Cari lirik via syncedlyrics. Return None jika tidak ditemukan."""
        log = get_logger()
        if not self._ensure_initialized():
            return None

        clean_query = track.clean_search_query()
        log.debug("syncedlyrics search: query='%s'", clean_query)

        try:
            lrc_text = None
            for p in ("Musixmatch", "NetEase", "Megalobiz"):
                if provider_is_tripped(p):
                    log.info("⏭️ %s dilewati untuk sisa sesi ini (gagal 3x berturut)", p)
                    continue

                try:
                    # Fase L: NetEase rawan hang — bungkus dengan wall-clock timeout
                    timeout = 20.0 if p == "NetEase" else _PROVIDER_CALL_TIMEOUT
                    lrc_text = call_with_timeout(
                        self._search_fn, clean_query, providers=[p], timeout=timeout
                    )
                    if lrc_text:
                        record_provider_success(p)
                        break
                    lrc_text = None  # hasil kosong = miss sah, bukan kegagalan
                except TimeoutError as e:
                    record_provider_fail(p)
                    log.warning("syncedlyrics %s TIMEOUT (%s) — lanjut provider berikutnya", p, e)
                    lrc_text = None
                except Exception as e:
                    record_provider_fail(p)
                    log.warning("syncedlyrics %s gagal: %s", p, e)
                    lrc_text = None

            if not lrc_text:
                raw_query = track.search_query()
                if raw_query != clean_query:
                    log.debug("syncedlyrics retry with raw query: '%s'", raw_query)
                    try:
                        lrc_text = self._search_fn(raw_query)
                    except Exception as e:
                        log.warning("syncedlyrics raw query gagal: %s", e)
                        lrc_text = None

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

        # === Fase L: cek negative cache — track ini baru saja dicari & kosong ===
        try:
            from mmpd.cache import is_lyrics_known_missing
            if is_lyrics_known_missing(track.title, track.artist, track.isrc):
                self._log.info(
                    "Negative cache HIT (lirik sudah dicari & tidak ada, TTL 24 jam): %s",
                    track.title,
                )
                return None
        except ImportError:
            pass
        except Exception as e:
            self._log.warning("Negative cache read error: %s", e)

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

        # Fase L: catat ke negative cache (TTL pendek, PISAH dari cache utama)
        # supaya run berikutnya tidak spam provider untuk lagu yang sama.
        try:
            from mmpd.cache import set_lyrics_not_found
            set_lyrics_not_found(track.title, track.artist, track.isrc)
        except Exception:
            pass
        return None


def _mmpd_version() -> str:
    """User-Agent version string dari mmpd.__version__ (bukan hardcode)."""
    try:
        from mmpd import __version__
        return __version__
    except ImportError:
        return "dev"


def build_default_chain(title: str = "") -> LyricsChain:
    """
    B4: Urutan dinamis berdasarkan script judul (NetEase diutamakan untuk CJK/Thai).
    """
    from mmpd.lyrics import detect_script
    script = detect_script(title) if title else "latin"
    
    # Default: Barat/Latin
    chain = [MusixmatchProvider(), LrclibProvider(), SyncedLyricsProvider()]
    
    if script in ("ja", "zh", "ko", "th"):
        # Untuk CJK & Thai, SyncedLyricsProvider (NetEase/Megalobiz) punya katalog lebih baik
        chain = [SyncedLyricsProvider(), MusixmatchProvider(), LrclibProvider()]
        
    return LyricsChain(chain)
