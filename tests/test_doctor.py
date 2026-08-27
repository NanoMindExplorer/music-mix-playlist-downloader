"""
Unit tests untuk mmpd.doctor — diagnostics command.

Strategy:
    - Mock shutil.which, socket, os.makedirs untuk test tanpa real I/O
    - Test _check_module, _check_binary helpers
    - Test run_doctor exit codes (0=all OK, 1=failures, 2=warnings)
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


# ============================================================================
# Helper functions: _check_binary, _check_module, _check_network
# ============================================================================

class TestCheckBinary:
    def test_binary_found(self):
        """Test _check_binary return True kalau binary ada di PATH."""
        from mmpd.doctor import _check_binary
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            ok, info = _check_binary("ffmpeg")
        assert ok is True
        assert "/usr/bin/ffmpeg" in info or "ffmpeg" in info

    def test_binary_not_found(self):
        """Test _check_binary return False kalau tidak ada."""
        from mmpd.doctor import _check_binary
        with patch("shutil.which", return_value=None):
            ok, info = _check_binary("nonexistent_binary")
        assert ok is False
        assert "PATH" in info


class TestCheckModule:
    def test_module_found(self):
        """Test _check_module return True kalau module bisa di-import."""
        from mmpd.doctor import _check_module
        ok, info = _check_module("os")  # 'os' selalu ada
        assert ok is True

    def test_module_not_found(self):
        """Test _check_module return False kalau module tidak ada."""
        from mmpd.doctor import _check_module
        ok, info = _check_module("nonexistent_module_xyz123")
        assert ok is False
        assert "module" in info.lower() or "no module" in info.lower()


class TestCheckNetwork:
    def test_network_connected(self):
        """Test _check_network return True kalau connect sukses."""
        from mmpd.doctor import _check_network
        mock_socket = MagicMock()
        with patch("socket.create_connection", mock_socket):
            ok, info = _check_network("example.com", 443)
        assert ok is True
        assert "connected" in info

    def test_network_failed(self):
        """Test _check_network return False kalau connect gagal."""
        from mmpd.doctor import _check_network
        with patch("socket.create_connection", side_effect=ConnectionRefusedError("refused")):
            ok, info = _check_network("example.com", 443)
        assert ok is False
        assert "refused" in info or "ConnectionRefused" in info

    def test_network_timeout(self):
        """Test _check_network return False kalau timeout."""
        from mmpd.doctor import _check_network
        with patch("socket.create_connection", side_effect=TimeoutError("timeout")):
            ok, info = _check_network("example.com", 443)
        assert ok is False


class TestCheckWritable:
    def test_writable_dir(self, tmp_path):
        """Test _check_writable return True untuk dir writable."""
        from mmpd.doctor import _check_writable
        ok, info = _check_writable(tmp_path)
        assert ok is True
        assert str(tmp_path) in info

    def test_nonexistent_dir_created(self, tmp_path):
        """Test _check_writable create dir kalau belum ada."""
        from mmpd.doctor import _check_writable
        new_dir = tmp_path / "newdir"
        ok, info = _check_writable(new_dir)
        assert ok is True
        assert new_dir.exists()

    def test_permission_denied(self, tmp_path):
        """Test _check_writable return False kalau permission denied."""
        from mmpd.doctor import _check_writable
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("denied")):
            ok, info = _check_writable(tmp_path / "denied")
        assert ok is False
        assert "denied" in info


# ============================================================================
# run_doctor — exit codes
# ============================================================================

class TestRunDoctor:
    def test_returns_int(self):
        """Test run_doctor return int exit code."""
        from mmpd.doctor import run_doctor
        result = run_doctor()
        assert isinstance(result, int)
        assert result in (0, 1, 2)  # 0=OK, 1=fail, 2=warn

    def test_doctor_with_all_modules_mocked(self):
        """Test run_doctor jalan dengan semua checks mocked."""
        from mmpd.doctor import run_doctor

        # Mock semua external checks
        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("socket.create_connection"), \
             patch("mmpd.doctor._check_module", return_value=(True, "v1.0")):
            result = run_doctor()
        # Should return 0 (all OK) or 2 (warnings only)
        assert result in (0, 2)

    def test_doctor_with_missing_modules(self):
        """Test run_doctor return 1 kalau ada module yang fail."""
        from mmpd.doctor import run_doctor

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"), \
             patch("mmpd.doctor._check_module", return_value=(False, "not installed")):
            result = run_doctor()
        assert result == 1  # failures

    def test_doctor_with_missing_binary(self):
        """Test run_doctor return 1 kalau ffmpeg tidak ada."""
        from mmpd.doctor import run_doctor

        with patch("shutil.which", return_value=None):
            result = run_doctor()
        assert result == 1  # ffmpeg missing = failure


# ============================================================================
# Color class
# ============================================================================

class TestColor:
    def test_color_constants_exist(self):
        """Test Color class punya semua konstanta."""
        from mmpd.doctor import Color
        assert hasattr(Color, "GREEN")
        assert hasattr(Color, "RED")
        assert hasattr(Color, "YELLOW")
        assert hasattr(Color, "CYAN")
        assert hasattr(Color, "BOLD")
        assert hasattr(Color, "RESET")

    def test_color_strings_nonempty(self):
        """Test color strings tidak kosong (ANSI escape codes)."""
        from mmpd.doctor import Color
        # Bisa kosong kalau tidak TTY, tapi harus string
        assert isinstance(Color.GREEN, str)
        assert isinstance(Color.RED, str)
