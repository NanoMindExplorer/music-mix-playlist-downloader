"""
Pytest configuration & shared fixtures untuk mmpd test suite.

Fixtures yang tersedia:
    tmp_output_dir     — temporary directory untuk test file ops
    mock_track_info    — TrackInfo dengan data realistis
    mock_lyrics_result — LyricsResult dengan synced LRC sample
    mock_spotify_track — SpotifyTrack dengan ISRC
    mock_youtube_entry — dict metadata YouTube (untuk mock yt_dlp)
    reset_mmpd_singletons — reset config & logger singleton antar test
    sample_lrc_content — sample .lrc file content untuk transliteration test
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Pastikan repo root ada di sys.path agar `import mmpd` & `import downloader` jalan
# bahkan ketika pytest dijalankan dari subdir tests/
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ============================================================================
# Auto-reset singleton state antar test
# ============================================================================

@pytest.fixture(autouse=True)
def reset_mmpd_singletons():
    """Reset singleton state (config, logger, spotify_client) antar test."""
    # Reset sebelum test
    from mmpd import config as _config
    from mmpd.logger import _logger as _logger_module
    from mmpd import spotify_client as _spotify_client

    _config.reset_config()
    # Reset logger module state
    import mmpd.logger as _log_mod
    _log_mod._logger = None
    _log_mod._initialized = False
    _spotify_client.reset_spotify_client()

    # Fase 4: reset cache singleton + clear all entries antar test
    # supaya test LyricsChain tidak kena cache dari test sebelumnya
    try:
        from mmpd import cache as _cache
        _cache.reset_cache_singleton()
        _cache.clear_all_cache()
    except Exception:
        pass  # cache module mungkin tidak terinstal

    yield  # run test

    # Reset setelah test (untuk test berikutnya)
    _config.reset_config()
    _log_mod._logger = None
    _log_mod._initialized = False
    _spotify_client.reset_spotify_client()

    # Fase 4: clear cache setelah test juga
    try:
        from mmpd import cache as _cache
        _cache.reset_cache_singleton()
        _cache.clear_all_cache()
    except Exception:
        pass


# ============================================================================
# File system fixtures
# ============================================================================

@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Temporary directory untuk test file ops (auto-cleanup oleh pytest)."""
    output = tmp_path / "output"
    output.mkdir()
    return output


@pytest.fixture
def tmp_lrc_file(tmp_path: Path) -> Path:
    """File .lrc kosong untuk test."""
    lrc = tmp_path / "test_song.lrc"
    lrc.write_text("", encoding="utf-8")
    return lrc


@pytest.fixture
def sample_lrc_content() -> str:
    """Sample LRC content dengan timestamp (untuk test transliteration/translation)."""
    return """[00:00.00]ただいま
[00:02.50]おかえり
[00:05.00]愛してる
[00:07.50]さようなら
"""


@pytest.fixture
def sample_lrc_chinese() -> str:
    """Sample LRC Mandarin (untuk test pinyin transliteration)."""
    return """[00:00.00]我爱你
[00:02.00]你好吗
[00:04.00]再见
"""


@pytest.fixture
def sample_lrc_korean() -> str:
    """Sample LRC Korean (untuk test romanizer)."""
    return """[00:00.00]안녕하세요
[00:02.00]사랑해요
"""


# ============================================================================
# TrackInfo / LyricsResult / SpotifyTrack fixtures
# ============================================================================

@pytest.fixture
def mock_track_info():
    """TrackInfo dengan data realistis."""
    from mmpd.types import TrackInfo
    return TrackInfo(
        title="Hello",
        artist="Adele",
        album="25",
        duration=295.0,
        isrc="GBBKS1500214",
    )


@pytest.fixture
def mock_track_no_isrc():
    """TrackInfo tanpa ISRC (untuk test fallback fuzzy matching)."""
    from mmpd.types import TrackInfo
    return TrackInfo(
        title="Random Song",
        artist="Unknown Artist",
        duration=180.0,
    )


@pytest.fixture
def mock_lyrics_result_synced():
    """LyricsResult dengan synced lyrics (LRC format)."""
    from mmpd.types import LyricsResult
    return LyricsResult(
        synced_lyrics="[00:00.00]Hello world\n[00:02.50]Second line",
        plain_lyrics="Hello world\nSecond line",
        provider="lrclib",
        track_name="Hello",
        artist_name="Adele",
        duration_ms=295000,
    )


@pytest.fixture
def mock_lyrics_result_plain_only():
    """LyricsResult hanya plain (no synced)."""
    from mmpd.types import LyricsResult
    return LyricsResult(
        synced_lyrics="",
        plain_lyrics="Just plain text without timestamps",
        provider="syncedlyrics",
    )


@pytest.fixture
def mock_spotify_track():
    """SpotifyTrack dengan ISRC + duration (untuk ISRC matching test)."""
    from mmpd.spotify_client import SpotifyTrack
    return SpotifyTrack(
        title="Hello",
        artist="Adele",
        album="25",
        duration_ms=295000,
        isrc="GBBKS1500214",
        spotify_url="https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
        popularity=85,
        explicit=False,
    )


@pytest.fixture
def mock_spotify_track_no_isrc():
    """SpotifyTrack tanpa ISRC (untuk test fuzzy fallback)."""
    from mmpd.spotify_client import SpotifyTrack
    return SpotifyTrack(
        title="Cover Song",
        artist="Indie Artist",
        duration_ms=200000,
    )


# ============================================================================
# Mock YouTube metadata (untuk mock yt_dlp)
# ============================================================================

@pytest.fixture
def mock_youtube_entry_isrc():
    """Mock YouTube entry dengan ISRC di external_ids (match ISRC Spotify)."""
    return {
        "webpage_url": "https://www.youtube.com/watch?v=abc123",
        "url": "https://www.youtube.com/watch?v=abc123",
        "title": "Adele - Hello (Official Music Video)",
        "duration": 295,
        "uploader": "AdeleVEVO",
        "channel": "AdeleVEVO",
        "external_ids": {
            "isrc": "GBBKS1500214",  # Match dengan mock_track_info
        },
        "track": "Hello",
        "artist": "Adele",
    }


@pytest.fixture
def mock_youtube_entry_no_isrc():
    """Mock YouTube entry tanpa ISRC (untuk test fuzzy matching)."""
    return {
        "webpage_url": "https://www.youtube.com/watch?v=xyz789",
        "url": "https://www.youtube.com/watch?v=xyz789",
        "title": "Hello - Adele (Lyrics)",
        "duration": 297,
        "uploader": "LyricsChannel",
        "external_ids": {},  # No ISRC
        "track": None,
        "artist": None,
    }


@pytest.fixture
def mock_youtube_entries_list(mock_youtube_entry_isrc, mock_youtube_entry_no_isrc):
    """List mock YouTube entries (3 candidates dengan 1 ISRC match)."""
    third_entry = {
        "webpage_url": "https://www.youtube.com/watch?v=def456",
        "url": "https://www.youtube.com/watch?v=def456",
        "title": "Hello Cover by Indie Band",
        "duration": 250,
        "uploader": "IndieBand",
        "external_ids": {},
    }
    return [mock_youtube_entry_isrc, mock_youtube_entry_no_isrc, third_entry]


# ============================================================================
# Environment fixtures (mock Termux/Linux/Windows)
# ============================================================================

@pytest.fixture
def mock_termux_env(monkeypatch):
    """Mock environment variables seolah berjalan di Termux."""
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    return monkeypatch


@pytest.fixture
def mock_linux_env(monkeypatch):
    """Mock environment variables seolah berjalan di Linux (bukan Termux)."""
    monkeypatch.delenv("PREFIX", raising=False)
    return monkeypatch


# ============================================================================
# Markers untuk skip test tertentu
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with -m 'not slow')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests that need real network (deselect with -m 'not integration')"
    )
    config.addinivalue_line(
        "markers", "requires_yt_dlp: marks tests that need yt-dlp runtime (not mockable)"
    )
