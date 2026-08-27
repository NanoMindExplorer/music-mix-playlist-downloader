# Changelog

Semua perubahan penting di project ini akan didokumentasikan di sini.

Format berdasarkan [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
dan project ini mengikuti [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] — 2026-08-27

### 🎉 Major Release — Production Ready

Fase 5 (Final Polish) selesai. Project sekarang production-ready dengan
376 tests, 79% coverage, CI/CD otomatis, dan dokumentasi lengkap.

### Added
- **376 unit tests** (+43 dari Fase 4, total 376), coverage **79%**
- **`tests/test_modes_organizer.py`** (8 tests) — Mode 3 Auto-Organizer
- **`tests/test_doctor.py`** (16 tests) — diagnostics command
- **`tests/test_logger.py`** (18 tests) — structured logging + rotation
- **`.pre-commit-config.yaml`** — ruff + black + mypy auto-run sebelum commit
- **`CONTRIBUTING.md`** — guide lengkap untuk kontributor
- **`docs/CHANGELOG.md`** — changelog v3.0 → v4.0

### Changed
- **`mmpd/spotify.py`** — hapus legacy scraping fallback, HANYA pakai spotipy
- **`tests/test_spotify.py`** — rewrite untuk test spotipy path (no legacy mock)
- **Coverage threshold** 75% → 78% (actual: 79%)
- **`mmpd/logger.py`** coverage: 74% → **91%** ⬆️
- **`mmpd/spotify.py`** coverage: 65% → **89%** ⬆️

### Removed
- **`spotify_parser.py`** — DEPRECATED sejak Fase 4, sekarang dihapus
  * Pakai `mmpd.spotify_client.SpotifyClient` (official API via spotipy)
  * Migration: `from spotify_parser import parse_spotify_url` → `from mmpd.spotify import parse_spotify_url_v2`

---

## [3.5.0] — 2026-08-27

### Added
- **`mmpd/cache.py`** (310 baris) — SQLite translation + lyrics cache
  - Translation cache: SHA256(source_text + lang) → translated_text (never expire)
  - Lyrics cache: SHA256(title + artist + isrc) → lyrics (TTL 30 hari)
  - Thread-safe via threading.Lock
  - DB location: config.cache_dir / cache.db
- **`tests/test_cache.py`** (20 tests) — cache hit/miss/expire/persist
- **`tests/test_ytdlp.py`** (29 tests) — YTDLPLogger + opts builder + hooks
- **`tests/test_ui.py`** (16 tests) — constants + theme + helpers
- **`tests/test_spotify.py`** (34 tests) — URL parser + fallback chain

### Changed
- **`mmpd/lyrics.py`** — integrate translation cache (100% hit → skip API)
- **`mmpd/lyrics_providers.py`** — integrate lyrics cache di LyricsChain
- **`tests/conftest.py`** — auto-reset cache singleton antar test
- **Coverage threshold** 70% → 75% (actual: 77%)
- **Performance**: 10x speedup untuk re-download playlist (cache hit)

### Deprecated
- **`spotify_parser.py`** — mark deprecated, akan dihapus di v4.0

### Fixed
- **Termux ruff install** — `requirements-dev.txt` tambah marker `sys_platform != android`
- **Bug** di `_transliterate_*` helpers (found via testing di Fase 3, fixed)

---

## [3.4.0] — 2026-08-27

### Added
- **234 unit tests** (10 test files, 234 test cases)
- **`tests/conftest.py`** — shared fixtures (mock_track_info, mock_youtube_entry, dll)
- **`tests/README.md`** — dokumentasi test suite
- **`.github/workflows/ci.yml`** — GitHub Actions CI/CD
  - Test matrix: Python 3.9, 3.10, 3.11, 3.12, 3.13, 3.14
  - Cross-platform: ubuntu-latest + macos-latest
  - Steps: syntax check → pytest --cov → Codecov → mypy → ruff → build wheel
- **Coverage config** di `pyproject.toml` (fail_under=70)

### Changed
- **Coverage** 72% (234 tests, 0 failures)
- **`.gitignore`** — tambah test artifacts (.coverage, htmlcov/, .pytest_cache/)

### Fixed
- **Bug production** di `mmpd/lyrics.py`: 4 transliteration helper functions
  salah skip baris dengan timestamp. Fix: pakai `if text:` bukan `not startswith("[")`

---

## [3.3.0] — 2026-08-27

### Added
- **`mmpd/spotify_client.py`** (290 baris) — Spotify official API via spotipy
  - SpotifyClient class dengan lazy init + retry + rate limit handling
  - SpotifyTrack dataclass (title, artist, album, isrc, duration_ms, dll)
  - Client Credentials flow (no user auth)
  - Exponential backoff retry (1s → 2s → 4s)
- **`mmpd/isrc_matcher.py`** (185 baris) — ISRC-based YouTube matching
  - 3-tier strategy: ISRC match (99%+) → fuzzy+duration → pure fuzzy
  - YouTubeMatchResult dataclass
- **`mmpd/concurrent.py`** (130 baris) — ThreadPoolExecutor wrapper
  - 3 worker paralel (3x speedup untuk playlist)
  - Exception isolation
- **`mmpd/doctor.py`** — cek Spotify credentials (SPOTIPY_CLIENT_ID/SECRET)

### Changed
- **`mmpd/spotify.py`** — fallback chain: spotipy → legacy scraping
- **`mmpd/modes/download.py`** — integrate ISRC matcher + concurrent downloads
  - Prompt user opt-in untuk concurrent + ISRC matching
- **`spotipy`** jadi required dependency

---

## [3.2.0] — 2026-08-27

### Added
- **`downloader.py` turun dari 1165 → 142 baris** (-88%)
- **11 modul modular baru**:
  - `mmpd/utils/ffmpeg.py` — subprocess wrapper FFmpeg
  - `mmpd/utils/fs.py` — atomic write, file ops
  - `mmpd/utils/matching.py` — rapidfuzz wrapper, query cleaning
  - `mmpd/modes/download.py` — Mode 1/4/5 (YouTube/Spotify/SoundCloud)
  - `mmpd/modes/retrofit.py` — Mode 2 (Perbaiki file lama)
  - `mmpd/modes/organizer.py` — Mode 3 (Auto-organizer)
  - `mmpd/lyrics.py` — transliteration + translation + sync + fetch
  - `mmpd/ytdlp.py` — YTDLPLogger + opts builder + hooks
  - `mmpd/spotify.py` — URL parser wrapper
  - `mmpd/ui.py` — banner, theme, helpers

### Changed
- Clear separation of concerns: UI / business logic / file ops / mode handlers
- Backward compatible via re-export di `downloader.py`

---

## [3.1.0] — 2026-08-27

### Added
- **Package `mmpd/`** dengan `pyproject.toml` (PEP 621 packaging)
- **Multi-entry point**:
  - `python downloader.py` (backward compatible)
  - `python -m mmpd` (module entry)
  - `mmpd` (entry point setelah `pip install .`)
- **`mmpd doctor`** — diagnostics command (5 kategori check)
- **`mmpd/config.py`** — centralized AppConfig (Termux/Linux/Windows)
- **`mmpd/logger.py`** — structured logging dengan file rotation (10MB, keep 5)
- **`mmpd/lyrics_providers.py`** — LyricsProvider abstraction
  - LrclibProvider (gratis, no-auth, database terbesar)
  - SyncedLyricsProvider (wrapper syncedlyrics)
  - LyricsChain fallback chain
- **`mmpd/types.py`** — TrackInfo, LyricsResult, LyricsProvider Protocol
- **`requirements-dev.txt`** — pytest, mypy, ruff, black

---

## [3.0.0] — 2026-08-27

### Initial Release (sebelum Fase 1)

- CLI interaktif dengan 5 mode operasi
- YouTube/SoundCloud/Spotify download via yt-dlp
- AI Lyrics Engine (transliteration + translation bilingual)
- FFmpeg audio conversion (MP3/FLAC/WAV)
- Cover art injection
- Huawei/HarmonyOS Musiclrc sync
- Anti-duplicate archive
- Termux Android support

---

## Version History Summary

| Version | Date       | Tests | Coverage | Highlight                          |
|---------|------------|-------|----------|------------------------------------|
| 3.0.0   | 2026-08-27 | 0     | 0%       | Initial release                    |
| 3.1.0   | 2026-08-27 | 0     | 0%       | Package mmpd/ + LRCLIB + doctor    |
| 3.2.0   | 2026-08-27 | 0     | 0%       | Module extraction (1165→142 baris) |
| 3.3.0   | 2026-08-27 | 0     | 0%       | Spotify API + ISRC + concurrent    |
| 3.4.0   | 2026-08-27 | 234   | 72%      | Unit tests + CI/CD                 |
| 3.5.0   | 2026-08-27 | 333   | 77%      | Cache (SQLite) + deprecate legacy  |
| **4.0.0** | **2026-08-27** | **376** | **79%** | **Production ready — hapus legacy** |
