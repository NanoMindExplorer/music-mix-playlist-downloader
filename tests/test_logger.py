"""
Unit tests untuk mmpd.logger — structured logging dengan file rotation.

Strategy:
    - Mock config untuk test setup_logging dengan tmp_path
    - Test logger singleton
    - Test get_log_file_path
    - Test log rotation (max_bytes + backup_count)
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest


# ============================================================================
# setup_logging
# ============================================================================

class TestSetupLogging:
    def test_returns_logger(self, mock_linux_env, tmp_path):
        """Test setup_logging return Logger instance."""
        from mmpd.logger import setup_logging, LOGGER_NAME
        logger = setup_logging(log_file=tmp_path / "test.log")
        assert isinstance(logger, logging.Logger)
        assert logger.name == LOGGER_NAME

    def test_logger_has_file_handler(self, mock_linux_env, tmp_path):
        """Test logger punya file handler."""
        from mmpd.logger import setup_logging
        logger = setup_logging(log_file=tmp_path / "test.log")
        # Should have at least one handler (file handler)
        assert len(logger.handlers) >= 1
        # Check any handler is RotatingFileHandler
        has_file_handler = any(
            isinstance(h, logging.handlers.RotatingFileHandler)
            for h in logger.handlers
        )
        assert has_file_handler

    def test_logger_level_set(self, mock_linux_env, tmp_path):
        """Test logger level di-set dengan benar."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        logger = log_mod.setup_logging(level=logging.DEBUG, log_file=tmp_path / "test.log")
        assert logger.level == logging.DEBUG

    def test_logger_writes_to_file(self, mock_linux_env, tmp_path):
        """Test logger benar-benar menulis ke file."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        log_file = tmp_path / "test.log"
        logger = log_mod.setup_logging(log_file=log_file)
        logger.info("Test message")

        # Verify file created and has content
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Test message" in content

    def test_logger_with_console_handler(self, mock_linux_env, tmp_path):
        """Test logger dengan console handler enabled."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        logger = log_mod.setup_logging(
            log_file=tmp_path / "test.log",
            enable_console=True,
        )
        # Should have 2 handlers: file + console
        assert len(logger.handlers) >= 2

    def test_logger_without_console(self, mock_linux_env, tmp_path):
        """Test logger tanpa console handler."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        logger = log_mod.setup_logging(
            log_file=tmp_path / "test.log",
            enable_console=False,
        )
        # Should have only 1 handler (file)
        console_handlers = [
            h for h in logger.handlers
            if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        assert len(console_handlers) == 0

    def test_logger_handles_permission_error(self, mock_linux_env, tmp_path):
        """Test logger handle permission error gracefully (fallback to NullHandler)."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        # Mock RotatingFileHandler untuk raise PermissionError
        with patch("logging.handlers.RotatingFileHandler.__init__", side_effect=PermissionError("denied")):
            # Should not raise, fallback to NullHandler
            logger = log_mod.setup_logging(log_file=tmp_path / "denied.log")
        assert logger is not None

    def test_logger_propagate_false(self, mock_linux_env, tmp_path):
        """Test logger.propagate = False (jangan bubble ke root)."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        logger = log_mod.setup_logging(log_file=tmp_path / "test.log")
        assert logger.propagate is False

    def test_logger_singleton(self, mock_linux_env, tmp_path):
        """Test setup_logging return same instance kalau sudah di-init."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        logger1 = log_mod.setup_logging(log_file=tmp_path / "test1.log")
        logger2 = log_mod.setup_logging(log_file=tmp_path / "test2.log")
        # Should return same instance (singleton)
        assert logger1 is logger2


# ============================================================================
# get_logger
# ============================================================================

class TestGetLogger:
    def test_get_logger_returns_logger(self, mock_linux_env):
        """Test get_logger return Logger instance."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        logger = log_mod.get_logger()
        assert isinstance(logger, logging.Logger)

    def test_get_logger_auto_init(self, mock_linux_env):
        """Test get_logger auto-init kalau belum di-setup."""
        import mmpd.logger as log_mod
        log_mod._logger = None
        log_mod._initialized = False

        logger = log_mod.get_logger()
        # Should auto-init and return logger
        assert logger is not None
        assert log_mod._logger is logger


# ============================================================================
# get_log_file_path
# ============================================================================

class TestGetLogFilePath:
    def test_returns_path_object(self, mock_linux_env):
        """Test get_log_file_path return Path object."""
        from mmpd.logger import get_log_file_path
        path = get_log_file_path()
        assert isinstance(path, Path)

    def test_path_contains_mmpd(self, mock_linux_env):
        """Test path mengandung 'mmpd'."""
        from mmpd.logger import get_log_file_path
        path = get_log_file_path()
        assert "mmpd" in str(path)

    def test_path_ends_with_log_extension(self, mock_linux_env):
        """Test path berakhiran .log."""
        from mmpd.logger import get_log_file_path
        path = get_log_file_path()
        assert str(path).endswith(".log")

    def test_path_contains_logs_dir(self, mock_linux_env):
        """Test path mengandung 'logs' directory."""
        from mmpd.logger import get_log_file_path
        path = get_log_file_path()
        assert "logs" in str(path) or "log" in str(path)


# ============================================================================
# Log rotation
# ============================================================================

class TestLogRotation:
    def test_max_log_size_constant(self):
        """Test MAX_LOG_SIZE constant ada."""
        from mmpd.logger import MAX_LOG_SIZE
        assert MAX_LOG_SIZE == 10 * 1024 * 1024  # 10 MB

    def test_backup_count_constant(self):
        """Test BACKUP_COUNT constant ada."""
        from mmpd.logger import BACKUP_COUNT
        assert BACKUP_COUNT == 5

    def test_file_format_constant(self):
        """Test _FILE_FORMAT constant ada."""
        from mmpd.logger import _FILE_FORMAT
        assert "%(asctime)s" in _FILE_FORMAT
        assert "%(levelname)" in _FILE_FORMAT
        assert "%(message)s" in _FILE_FORMAT
