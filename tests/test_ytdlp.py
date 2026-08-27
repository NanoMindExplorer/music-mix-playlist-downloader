"""
Unit tests untuk mmpd.ytdlp — YTDLPLogger + opts builder + hooks.

Strategy:
    - Test build_download_opts + build_retrofit_opts return dict dengan keys expected
    - Test YTDLPLogger filter error noise
    - Test default_download_hook callback behavior
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mmpd.ytdlp import (
    YTDLPLogger,
    build_default_postprocessors,
    build_download_opts,
    build_retrofit_opts,
    default_download_hook,
)


# ============================================================================
# YTDLPLogger
# ============================================================================

class TestYTDLPLogger:
    def test_debug_silent(self):
        """Test debug() tidak raise apa-apa."""
        logger = YTDLPLogger()
        logger.debug("some debug message")
        # Should not raise

    def test_warning_silent(self):
        """Test warning() tidak raise apa-apa."""
        logger = YTDLPLogger()
        logger.warning("some warning")
        # Should not raise

    def test_error_metadata_ignored(self):
        """Test error dengan 'metadata' keyword di-ignore (tidak raise)."""
        logger = YTDLPLogger()
        logger.error("Failed to extract metadata")
        # Should not raise

    def test_error_thumbnail_ignored(self):
        """Test error dengan 'thumbnail' di-ignore."""
        logger = YTDLPLogger()
        logger.error("Failed to download thumbnail")
        # Should not raise

    def test_error_429_ignored(self):
        """Test error 429 (rate limit) di-ignore."""
        logger = YTDLPLogger()
        logger.error("HTTP Error 429: Too Many Requests")
        # Should not raise

    def test_error_subtitles_ignored(self):
        """Test error 'subtitles' di-ignore."""
        logger = YTDLPLogger()
        logger.error("Failed to download subtitles")
        # Should not raise

    def test_error_real_error_logged(self):
        """Test error yang BUKAN noise tetap di-log (tidak raise)."""
        logger = YTDLPLogger()
        logger.error("Failed to download video: Video unavailable")
        # Should not raise — tapi di internal akan log


# ============================================================================
# build_default_postprocessors
# ============================================================================

class TestBuildDefaultPostprocessors:
    def test_mp3_postprocessors(self):
        """Test PP untuk MP3."""
        pp = build_default_postprocessors("mp3", quality="320")
        assert any(p["key"] == "FFmpegExtractAudio" for p in pp)
        assert any(p["key"] == "FFmpegMetadata" for p in pp)
        assert any(p["key"] == "EmbedThumbnail" for p in pp)
        # Check quality
        extract_pp = next(p for p in pp if p["key"] == "FFmpegExtractAudio")
        assert extract_pp["preferredcodec"] == "mp3"
        assert extract_pp["preferredquality"] == "320"

    def test_flac_postprocessors(self):
        """Test PP untuk FLAC."""
        pp = build_default_postprocessors("flac", quality=None)
        assert any(p["key"] == "FFmpegExtractAudio" for p in pp)
        extract_pp = next(p for p in pp if p["key"] == "FFmpegExtractAudio")
        assert extract_pp["preferredcodec"] == "flac"
        assert "preferredquality" not in extract_pp

    def test_wav_no_embed_thumbnail(self):
        """Test WAV tidak embed thumbnail."""
        pp = build_default_postprocessors("wav", is_wav=True)
        assert not any(p["key"] == "EmbedThumbnail" for p in pp)

    def test_no_quality(self):
        """Test tanpa quality specified."""
        pp = build_default_postprocessors("mp3", quality=None)
        extract_pp = next(p for p in pp if p["key"] == "FFmpegExtractAudio")
        assert "preferredquality" not in extract_pp

    def test_embed_thumbnail_false(self):
        """Test embed_thumbnail=False."""
        pp = build_default_postprocessors("mp3", embed_thumbnail=False)
        assert not any(p["key"] == "EmbedThumbnail" for p in pp)


# ============================================================================
# build_download_opts
# ============================================================================

class TestBuildDownloadOpts:
    def test_basic_opts(self):
        """Test basic ydl_opts structure."""
        opts = build_download_opts("/tmp/%(title)s.%(ext)s", "mp3", quality="320")
        assert opts["format"] == "bestaudio/best"
        assert opts["outtmpl"] == "/tmp/%(title)s.%(ext)s"
        assert opts["noplaylist"] is False
        assert opts["ignoreerrors"] is True
        assert opts["geo_bypass"] is True
        assert opts["restrictfilenames"] is True  # Fase 1 fix
        assert opts["quiet"] is True
        assert "logger" in opts
        assert isinstance(opts["logger"], YTDLPLogger)

    def test_postprocessors_present(self):
        """Test postprocessors list ada."""
        opts = build_download_opts("/tmp/test.%(ext)s", "mp3", quality="320")
        assert "postprocessors" in opts
        assert len(opts["postprocessors"]) >= 2  # FFmpegExtractAudio + FFmpegMetadata

    def test_archive_file_set(self):
        """Test archive file untuk anti-duplicate."""
        opts = build_download_opts(
            "/tmp/test.%(ext)s", "mp3",
            archive_file="/tmp/archive.txt",
        )
        assert opts["download_archive"] == "/tmp/archive.txt"

    def test_no_archive_file_when_none(self):
        """Test archive_file tidak set kalau None."""
        opts = build_download_opts("/tmp/test.%(ext)s", "mp3", archive_file=None)
        assert "download_archive" not in opts

    def test_lyrics_from_youtube_cc(self):
        """Test subtitle download untuk Mode 3."""
        opts = build_download_opts(
            "/tmp/test.%(ext)s", "mp3",
            lyrics_from_youtube_cc=True,
        )
        assert opts["writesubtitles"] is True
        assert opts["writeautomaticsub"] is True
        assert "id" in opts["subtitleslangs"]
        assert any(p.get("key") == "FFmpegSubtitlesConvertor" for p in opts["postprocessors"])

    def test_no_subtitles_by_default(self):
        """Test tanpa subtitle download by default."""
        opts = build_download_opts("/tmp/test.%(ext)s", "mp3")
        assert "writesubtitles" not in opts or opts.get("writesubtitles") is False

    def test_max_songs_playlistend(self):
        """Test max_songs set playlistend."""
        opts = build_download_opts("/tmp/test.%(ext)s", "mp3", max_songs=10)
        assert opts["playlistend"] == 10

    def test_no_max_songs(self):
        """Test tanpa max_songs, playlistend tidak set."""
        opts = build_download_opts("/tmp/test.%(ext)s", "mp3", max_songs=None)
        assert "playlistend" not in opts

    def test_progress_hook_added(self):
        """Test progress_hook ditambahkan."""
        hook = lambda d: None
        opts = build_download_opts("/tmp/test.%(ext)s", "mp3", progress_hook=hook)
        assert hook in opts["progress_hooks"]

    def test_wav_no_writethumbnail(self):
        """Test WAV tidak writethumbnail."""
        opts = build_download_opts("/tmp/test.%(ext)s", "wav")
        assert "writethumbnail" not in opts or opts.get("writethumbnail") is False

    def test_mp3_writethumbnail_true(self):
        """Test MP3 writethumbnail True."""
        opts = build_download_opts("/tmp/test.%(ext)s", "mp3")
        assert opts.get("writethumbnail") is True


# ============================================================================
# build_retrofit_opts
# ============================================================================

class TestBuildRetrofitOpts:
    def test_basic_retrofit_opts(self):
        """Test retrofit opts structure."""
        opts = build_retrofit_opts("/tmp/temp_meta.%(ext)s")
        assert opts["format"] == "bestaudio/best"
        assert opts["skip_download"] is True
        assert opts["writethumbnail"] is True
        assert opts["restrictfilenames"] is True
        assert opts["quiet"] is True

    def test_retrofit_with_youtube_cc(self):
        """Test retrofit dengan subtitle download."""
        opts = build_retrofit_opts("/tmp/test.%(ext)s", lyrics_from_youtube_cc=True)
        assert opts["writesubtitles"] is True
        assert opts["writeautomaticsub"] is True
        assert any(p.get("key") == "FFmpegSubtitlesConvertor" for p in opts["postprocessors"])

    def test_retrofit_no_subtitles_by_default(self):
        """Test retrofit tanpa subtitle by default."""
        opts = build_retrofit_opts("/tmp/test.%(ext)s")
        assert "writesubtitles" not in opts

    def test_retrofit_retries(self):
        """Test retrofit punya retry config."""
        opts = build_retrofit_opts("/tmp/test.%(ext)s")
        assert opts["retries"] == 5
        assert opts["file_access_retries"] == 5
        assert opts["fragment_retries"] == 5


# ============================================================================
# default_download_hook
# ============================================================================

class TestDefaultDownloadHook:
    def test_hook_factory_returns_callable(self):
        """Test hook factory return callable."""
        progress = MagicMock()
        main_task = MagicMock()
        hook = default_download_hook(progress, main_task)
        assert callable(hook)

    def test_hook_downloading_status(self):
        """Test hook handle 'downloading' status."""
        progress = MagicMock()
        main_task = MagicMock()
        hook = default_download_hook(progress, main_task)

        hook({
            "status": "downloading",
            "total_bytes": 1000000,
            "downloaded_bytes": 500000,
            "filename": "/tmp/song.mp3",
        })
        # Verify progress.update dipanggil
        progress.update.assert_called()

    def test_hook_finished_status(self):
        """Test hook handle 'finished' status."""
        progress = MagicMock()
        main_task = MagicMock()
        hook = default_download_hook(progress, main_task)

        hook({
            "status": "finished",
            "filename": "/tmp/song.mp3",
        })
        # Verify progress.update dipanggil
        progress.update.assert_called()

    def test_hook_handles_missing_keys(self):
        """Test hook handle dict dengan keys missing."""
        progress = MagicMock()
        main_task = MagicMock()
        hook = default_download_hook(progress, main_task)

        # Should not raise kalau keys missing
        hook({"status": "downloading"})
        hook({"status": "finished"})

    def test_hook_unknown_status_ignored(self):
        """Test hook ignore status yang tidak dikenali."""
        progress = MagicMock()
        main_task = MagicMock()
        hook = default_download_hook(progress, main_task)

        hook({"status": "unknown_status"})
        # Should not raise
