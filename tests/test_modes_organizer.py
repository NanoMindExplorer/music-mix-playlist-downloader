"""
Unit tests untuk mmpd.modes.organizer — Mode 3 Auto-Organizer.

Strategy:
    - Mock questionary prompts (ask_confirm returns False untuk early exit)
    - Mock filesystem operations dengan tmp_path
    - Test match LRC dengan MP3 via rapidfuzz
    - Test move files ke folder Music + Musiclrc
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestRunOrganizer:
    def test_nonexistent_downloads_dir_returns(self, mock_linux_env, monkeypatch, tmp_path):
        """Test return early kalau folder Downloads tidak ada."""
        # Mock config dengan path yang tidak ada
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm") as mock_confirm:
            mock_confirm.return_value = True
            from mmpd.modes.organizer import run_organizer
            # Should not raise, just return (folder doesn't exist)
            run_organizer()

    def test_empty_downloads_dir_returns(self, mock_linux_env, monkeypatch, tmp_path):
        """Test return early kalau folder Downloads kosong."""
        # Create Downloads dir but empty
        downloads = tmp_path / "Downloads"
        downloads.mkdir()

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm", return_value=True):
            from mmpd.modes.organizer import run_organizer
            # Should not raise
            run_organizer()

    def test_user_cancel_returns_early(self, mock_linux_env, monkeypatch, tmp_path):
        """Test return early kalau user cancel di prompt konfirmasi."""
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        # Add dummy files
        (downloads / "song.mp3").touch()
        (downloads / "song.lrc").touch()

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm", return_value=False):
            from mmpd.modes.organizer import run_organizer
            run_organizer()
            # Should return early, files should still be in Downloads
            assert (downloads / "song.mp3").exists()

    def test_move_mp3_and_lrc_to_music_dir(self, mock_linux_env, monkeypatch, tmp_path):
        """Test move MP3 dan LRC ke folder Music + Musiclrc."""
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        # Create matching MP3 + LRC
        (downloads / "Adele Hello.mp3").write_bytes(b"mp3 data")
        (downloads / "Adele Hello.lrc").write_text("lyrics")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm", return_value=True):
            from mmpd.modes.organizer import run_organizer
            run_organizer()

        # Music dir should exist with MP3
        music_dir = tmp_path / "Downloads" / "Music"
        musiclrc_dir = music_dir / "Musiclrc"
        assert music_dir.exists()
        assert musiclrc_dir.exists()
        # MP3 moved to Music
        assert (music_dir / "Adele Hello.mp3").exists()
        # LRC moved to Musiclrc
        assert (musiclrc_dir / "Adele Hello.lrc").exists()
        # Original files should be gone
        assert not (downloads / "Adele Hello.mp3").exists()

    def test_lrc_without_matching_mp3_kept(self, mock_linux_env, monkeypatch, tmp_path):
        """Test LRC tanpa MP3 match tetap dipindah dengan nama asli."""
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        # LRC only, no matching MP3
        (downloads / "Unknown Song.lrc").write_text("lyrics")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm", return_value=True):
            from mmpd.modes.organizer import run_organizer
            run_organizer()

        musiclrc_dir = tmp_path / "Downloads" / "Music" / "Musiclrc"
        # LRC should still be moved (with original name since no match)
        assert (musiclrc_dir / "Unknown Song.lrc").exists()

    def test_mp3_without_lrc_still_moved(self, mock_linux_env, monkeypatch, tmp_path):
        """Test MP3 tanpa LRC tetap dipindah ke Music."""
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        (downloads / "Song Without LRC.mp3").write_bytes(b"data")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm", return_value=True):
            from mmpd.modes.organizer import run_organizer
            run_organizer()

        music_dir = tmp_path / "Downloads" / "Music"
        assert (music_dir / "Song Without LRC.mp3").exists()

    def test_fuzzy_match_lrc_to_mp3(self, mock_linux_env, monkeypatch, tmp_path):
        """Test fuzzy match LRC dengan nama mirip ke MP3."""
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        # MP3 dan LRC dengan nama sedikit beda
        (downloads / "Adele - Hello.mp3").write_bytes(b"data")
        (downloads / "Adele Hello.lrc").write_text("lyrics")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm", return_value=True):
            from mmpd.modes.organizer import run_organizer
            run_organizer()

        musiclrc_dir = tmp_path / "Downloads" / "Music" / "Musiclrc"
        # LRC should be renamed to match MP3
        assert (musiclrc_dir / "Adele - Hello.lrc").exists()

    def test_oserror_handling(self, mock_linux_env, monkeypatch, tmp_path):
        """Test OSError saat listdir tidak crash."""
        downloads = tmp_path / "Downloads"
        # Tidak create dir → os.listdir akan raise

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        with patch("mmpd.modes.organizer.ask_confirm", return_value=True):
            from mmpd.modes.organizer import run_organizer
            # Should not raise
            run_organizer()
