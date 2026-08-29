"""
Tests Fase R — reliability: backoff 429, singleton OpenCC, batching baru.
"""

from __future__ import annotations

import time as _time
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# request_with_backoff — retry 429/5xx dengan exponential backoff
# ============================================================================

class TestRequestWithBackoff:
    @pytest.fixture(autouse=True)
    def _fast_backoff(self, monkeypatch):
        """Percepat sleep supaya test cepat (backoff asli 1.5s+)."""
        from mmpd import lyrics_providers as lp
        monkeypatch.setattr(lp, "_BACKOFF_BASE", 0.01)
        yield

    def test_ok_first_try_no_retry(self):
        from mmpd.lyrics_providers import request_with_backoff

        requests_mock = MagicMock()
        response = MagicMock(status_code=200)
        requests_mock.get.return_value = response

        res = request_with_backoff(requests_mock, "https://x.test/api")
        assert res is response
        assert requests_mock.get.call_count == 1

    def test_429_retried_until_success(self):
        from mmpd.lyrics_providers import request_with_backoff

        requests_mock = MagicMock()
        fail = MagicMock(status_code=429)
        ok = MagicMock(status_code=200)
        requests_mock.get.side_effect = [fail, fail, ok]

        res = request_with_backoff(requests_mock, "https://x.test/api")
        assert res is ok
        assert requests_mock.get.call_count == 3

    def test_404_not_retried(self):
        """404 = tidak ditemukan (sah), TIDAK boleh di-retry."""
        from mmpd.lyrics_providers import request_with_backoff

        requests_mock = MagicMock()
        not_found = MagicMock(status_code=404)
        requests_mock.get.return_value = not_found

        res = request_with_backoff(requests_mock, "https://x.test/api")
        assert res is not_found
        assert requests_mock.get.call_count == 1

    def test_network_error_retried(self):
        from mmpd.lyrics_providers import request_with_backoff

        requests_mock = MagicMock()
        ok = MagicMock(status_code=200)
        requests_mock.get.side_effect = [ConnectionError("boom"), ok]

        res = request_with_backoff(requests_mock, "https://x.test/api")
        assert res is ok
        assert requests_mock.get.call_count == 2

    def test_gives_up_after_max_retries(self):
        from mmpd.lyrics_providers import request_with_backoff, _MAX_RETRIES

        requests_mock = MagicMock()
        requests_mock.get.side_effect = ConnectionError("down")
        with pytest.raises(ConnectionError):
            request_with_backoff(requests_mock, "https://x.test/api")
        assert requests_mock.get.call_count == _MAX_RETRIES + 1

    def test_timeout_default_applied(self):
        from mmpd.lyrics_providers import request_with_backoff

        requests_mock = MagicMock()
        ok = MagicMock(status_code=200)
        requests_mock.get.return_value = ok
        request_with_backoff(requests_mock, "https://x.test/api")
        _, kwargs = requests_mock.get.call_args
        assert kwargs.get("timeout") == (10, 30)


# ============================================================================
# OpenCC singleton (dulu converter baru per panggilan)
# ============================================================================

class TestOpenCCSingleton:
    def test_converter_reused(self):
        from mmpd.utils.matching import _get_opencc

        first = _get_opencc()
        second = _get_opencc()
        if first is not None:  # opencc terinstal
            assert first is second, "Converter OpenCC harus singleton (objek sama)"

    def test_normalize_query_fast_repeat(self):
        """100x normalize_track_query harus tetap cepat (singleton aktif)."""
        from mmpd.utils.matching import normalize_track_query

        t0 = _time.monotonic()
        for i in range(100):
            normalize_track_query(f"聽海 張惠妹 {i} (Official MV)")
        elapsed = _time.monotonic() - t0
        assert elapsed < 5.0, f"100x normalize terlalu lambat: {elapsed:.2f}s"


# ============================================================================
# Batch baru (snapshot mtime) — download non-interaktif
# ============================================================================

class TestNewBatchDetection:
    def test_snapshot_and_find_new(self, tmp_path):
        from mmpd.modes.download import _snapshot_audio_files, _find_new_audio_files

        # File lama
        old_mp3 = tmp_path / "old.mp3"
        old_mp3.write_bytes(b"x")
        before = _snapshot_audio_files(str(tmp_path))
        assert str(old_mp3) in before

        # Tidak ada file baru → kosong
        assert _find_new_audio_files(str(tmp_path), before) == []

        # File baru muncul
        new_mp3 = tmp_path / "new.mp3"
        new_mp3.write_bytes(b"y")
        new_files = _find_new_audio_files(str(tmp_path), before)
        assert [str(new_mp3)] == new_files

    def test_snapshot_missing_dir(self):
        from mmpd.modes.download import _snapshot_audio_files
        assert _snapshot_audio_files("/tidak/ada/dir/ini") == {}

    def test_ignores_non_audio_files(self, tmp_path):
        from mmpd.modes.download import _snapshot_audio_files, _find_new_audio_files

        before = {}
        (tmp_path / "cover.jpg").write_bytes(b"img")
        (tmp_path / "notes.txt").write_text("x")
        assert _find_new_audio_files(str(tmp_path), before) == []


# ============================================================================
# Retrofit non-interaktif — safety contract
# ============================================================================

class TestRetrofitNonInteractive:
    def test_existing_lrc_never_overwritten_by_default(self, tmp_path):
        """Kontrak Fase L: tanpa --overwrite, .lrc existing TIDAK di-fetch ulang."""
        from mmpd.modes.retrofit import run_retrofit_noninteractive

        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:01.00]lirik lama yang benar\n", encoding="utf-8")
        (tmp_path / "song.mp3").write_bytes(b"audio")

        with patch("mmpd.modes.retrofit.fetch_synced_lyrics") as mock_fetch, \
             patch("mmpd.modes.retrofit._process_cover_art_for_audio"), \
             patch("mmpd.modes.retrofit._cleanup_old_lrc_files", return_value=0):
            code = run_retrofit_noninteractive(
                folder=str(tmp_path),
                target="lyrics",
                fetch_missing=True,
                embed_id3=False,
                workers=1,
            )

        assert code == 0
        mock_fetch.assert_not_called(), (
            ".lrc yang sudah ada TIDAK boleh di-fetch ulang tanpa --overwrite"
        )
        assert "lirik lama yang benar" in lrc.read_text(encoding="utf-8")

    def test_missing_lrc_fetched_when_enabled(self, tmp_path):
        from mmpd.modes.retrofit import run_retrofit_noninteractive

        (tmp_path / "song.mp3").write_bytes(b"audio")

        with patch("mmpd.modes.retrofit.fetch_synced_lyrics") as mock_fetch, \
             patch("mmpd.modes.retrofit._process_cover_art_for_audio"), \
             patch("mmpd.modes.retrofit._cleanup_old_lrc_files", return_value=0):
            run_retrofit_noninteractive(
                folder=str(tmp_path), target="lyrics", fetch_missing=True,
                embed_id3=False, workers=1,
            )
        mock_fetch.assert_called_once()

    def test_missing_folder_exit_1(self, tmp_path):
        from mmpd.modes.retrofit import run_retrofit_noninteractive
        assert run_retrofit_noninteractive(folder=str(tmp_path / "nope")) == 1

    def test_overwrite_with_backup(self, tmp_path):
        """--overwrite: .lrc lama di-backup dulu ke .lrc.bak."""
        from mmpd.modes.retrofit import run_retrofit_noninteractive

        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:01.00]versi lama\n", encoding="utf-8")
        (tmp_path / "song.mp3").write_bytes(b"audio")

        def fake_fetch(title, lrc_path, **kwargs):
            with open(lrc_path, "w", encoding="utf-8") as f:
                f.write("[00:01.00]versi baru\n")

        with patch("mmpd.modes.retrofit.fetch_synced_lyrics", side_effect=fake_fetch), \
             patch("mmpd.modes.retrofit._process_cover_art_for_audio"), \
             patch("mmpd.modes.retrofit._cleanup_old_lrc_files", return_value=0):
            run_retrofit_noninteractive(
                folder=str(tmp_path), target="lyrics", overwrite_lrc=True,
                fetch_missing=True, embed_id3=False, workers=1,
            )

        assert "versi baru" in lrc.read_text(encoding="utf-8")
        backup = tmp_path / "song.lrc.bak"
        assert backup.exists(), "Backup .lrc.bak wajib dibuat saat --overwrite"
        assert "versi lama" in backup.read_text(encoding="utf-8")


# ============================================================================
# Config loader — workers clamp
# ============================================================================

class TestWorkersClamp:
    def test_workers_from_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MMPD_WORKERS", raising=False)
        from mmpd import config as config_mod, config_loader
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        config_mod.reset_config()
        config_loader.reset_config_loader()

        cfg = tmp_path / ".config" / "mmpd" / "config.toml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("[general]\nworkers = 2\n", encoding="utf-8")
        assert config_loader.get_workers() == 2
        config_loader.reset_config_loader()
        config_mod.reset_config()
