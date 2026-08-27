"""
Unit tests untuk mmpd.config — AppConfig dan path detection.

Coverage:
    - is_termux(), is_windows(), is_macos() env detection
    - AppConfig dataclass (Termux vs Linux vs Windows path)
    - get_config() singleton
    - get_output_dir(), get_default_path(), get_musiclrc_dir() helpers
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from mmpd.config import (
    AppConfig,
    get_config,
    get_default_path,
    get_musiclrc_dir,
    get_output_dir,
    is_macos,
    is_termux,
    is_windows,
    reset_config,
)


# ============================================================================
# is_termux, is_windows, is_macos
# ============================================================================

class TestEnvDetection:
    def test_is_termux_true(self, mock_termux_env):
        """Test deteksi Termux via PREFIX env var."""
        assert is_termux() is True

    def test_is_termux_false_no_prefix(self, mock_linux_env):
        """Test bukan Termux kalau PREFIX tidak ada."""
        assert is_termux() is False

    def test_is_termux_false_wrong_prefix(self, monkeypatch):
        """Test PREFIX ada tapi tidak mengandung com.termux."""
        monkeypatch.setenv("PREFIX", "/usr/local")  # Bukan Termux
        assert is_termux() is False

    def test_is_windows_on_linux(self):
        """Test is_windows() return False di Linux."""
        if os.name == "nt":
            pytest.skip("Test khusus Linux/macOS")
        assert is_windows() is False

    def test_is_macos_returns_bool(self):
        """Test is_macos() return boolean (tergantung OS test jalan)."""
        result = is_macos()
        assert isinstance(result, bool)


# ============================================================================
# AppConfig — Termux environment
# ============================================================================

class TestAppConfigTermux:
    def test_termux_output_dir(self, mock_termux_env, monkeypatch):
        """Test output_dir di Termux = ~/storage/downloads/YT_Downloader."""
        # Mock home directory
        fake_home = Path("/data/data/com.termux/files/home")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = AppConfig()
        assert config.is_termux is True
        assert "storage" in str(config.output_dir)
        assert "downloads" in str(config.output_dir)
        assert "YT_Downloader" in str(config.output_dir)

    def test_termux_music_dir(self, mock_termux_env, monkeypatch):
        """Test music_dir di Termux = ~/storage/shared/Music."""
        fake_home = Path("/data/data/com.termux/files/home")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = AppConfig()
        assert "shared" in str(config.music_dir)
        assert "Music" in str(config.music_dir)

    def test_termux_musiclrc_dir(self, mock_termux_env, monkeypatch):
        """Test musiclrc_dir di Termux = ~/storage/shared/Music/Musiclrc."""
        fake_home = Path("/data/data/com.termux/files/home")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = AppConfig()
        assert config.musiclrc_dir.name == "Musiclrc"

    def test_termux_log_dir_uses_prefix(self, mock_termux_env, monkeypatch):
        """Test log_dir di Termux pakai PREFIX/var/log."""
        fake_home = Path("/data/data/com.termux/files/home")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = AppConfig()
        assert "var" in str(config.log_dir)
        assert "log" in str(config.log_dir)
        assert "mmpd" in str(config.log_dir)

    def test_termux_cache_dir_uses_prefix(self, mock_termux_env, monkeypatch):
        """Test cache_dir di Termux pakai PREFIX/var/cache."""
        fake_home = Path("/data/data/com.termux/files/home")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = AppConfig()
        assert "var" in str(config.cache_dir)
        assert "cache" in str(config.cache_dir)


# ============================================================================
# AppConfig — Linux environment
# ============================================================================

class TestAppConfigLinux:
    def test_linux_output_dir(self, mock_linux_env, monkeypatch):
        """Test output_dir di Linux = ~/Downloads/YT_Downloader."""
        fake_home = Path("/home/testuser")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        config = AppConfig()
        assert config.is_termux is False
        assert "Downloads" in str(config.output_dir)
        assert "YT_Downloader" in str(config.output_dir)

    def test_linux_log_dir_uses_xdg(self, mock_linux_env, monkeypatch):
        """Test log_dir di Linux pakai ~/.local/share/mmpd/logs."""
        fake_home = Path("/home/testuser")
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)

        config = AppConfig()
        assert ".local" in str(config.log_dir)
        assert "share" in str(config.log_dir)
        assert "mmpd" in str(config.log_dir)
        assert "logs" in str(config.log_dir)

    def test_linux_log_dir_respects_xdg_env(self, mock_linux_env, monkeypatch):
        """Test log_dir pakai XDG_DATA_HOME jika ada."""
        xdg_data = Path("/custom/xdg/data")
        monkeypatch.setenv("XDG_DATA_HOME", str(xdg_data))

        config = AppConfig()
        assert str(config.log_dir).startswith("/custom/xdg/data")

    def test_linux_config_file_path(self, mock_linux_env, monkeypatch):
        """Test config_file pakai ~/.config/mmpd/config.toml."""
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        config = AppConfig()
        assert "config.toml" in str(config.config_file)
        assert "mmpd" in str(config.config_file)


# ============================================================================
# AppConfig — frozen dataclass behavior
# ============================================================================

class TestAppConfigFrozen:
    def test_appconfig_is_frozen(self, mock_linux_env, monkeypatch):
        """Test AppConfig adalah frozen dataclass (immutable)."""
        config = AppConfig()
        with pytest.raises(Exception):
            config.output_dir = "/somewhere/else"  # type: ignore


# ============================================================================
# get_config singleton
# ============================================================================

class TestGetConfigSingleton:
    def test_get_config_returns_instance(self, mock_linux_env):
        """Test get_config return AppConfig instance."""
        config = get_config()
        assert isinstance(config, AppConfig)

    def test_get_config_returns_same_instance(self, mock_linux_env):
        """Test singleton: get_config return instance yang sama."""
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2

    def test_reset_config_returns_new_instance(self, mock_linux_env):
        """Test reset_config membuat instance baru di get_config berikutnya."""
        c1 = get_config()
        reset_config()
        c2 = get_config()
        assert c1 is not c2


# ============================================================================
# Helper functions
# ============================================================================

class TestHelperFunctions:
    def test_get_output_dir_returns_string(self, mock_linux_env):
        """Test get_output_dir return string (bukan Path)."""
        result = get_output_dir()
        assert isinstance(result, str)
        assert "YT_Downloader" in result

    def test_get_default_path_alias_for_get_output_dir(self, mock_linux_env):
        """Test get_default_path() return same value as get_output_dir()."""
        assert get_default_path() == get_output_dir()

    def test_get_musiclrc_dir_returns_string(self, mock_linux_env):
        """Test get_musiclrc_dir return string."""
        result = get_musiclrc_dir()
        assert isinstance(result, str)
        assert "Musiclrc" in result


# ============================================================================
# AppConfig.ensure_dirs
# ============================================================================

class TestEnsureDirs:
    def test_ensure_dirs_creates_log_and_cache(self, mock_linux_env, tmp_path, monkeypatch):
        """Test ensure_dirs membuat log_dir dan cache_dir."""
        # Override log_dir dan cache_dir ke tmp_path
        config = AppConfig()
        # Pakai object.__setattr__ karena frozen
        object.__setattr__(config, "log_dir", tmp_path / "log")
        object.__setattr__(config, "cache_dir", tmp_path / "cache")
        object.__setattr__(config, "output_dir", tmp_path / "output")

        config.ensure_dirs()
        assert (tmp_path / "log").is_dir()
        assert (tmp_path / "cache").is_dir()
        assert (tmp_path / "output").is_dir()

    def test_ensure_dirs_idempotent(self, mock_linux_env, tmp_path, monkeypatch):
        """Test ensure_dirs pada direktori yang sudah ada tidak raise."""
        config = AppConfig()
        object.__setattr__(config, "log_dir", tmp_path / "log")
        object.__setattr__(config, "cache_dir", tmp_path / "cache")
        object.__setattr__(config, "output_dir", tmp_path / "output")
        # Buat dulu
        config.ensure_dirs()
        # Pastiin tidak raise saat dipanggil lagi
        config.ensure_dirs()
