"""
Structured Logging dengan File Rotation.

Sebelumnya, semua logging pakai `console.print()` saja — tidak ada persistensi.
Akibatnya, saat user mengalami error dan ingin debug retroaktif, tidak ada
log yang bisa diperiksa. Modul ini menyediakan:

- Logger `mmpd` yang menulis ke file dengan rotation (10 MB, keep 5 files)
- Mirror ke console (rich formatting) untuk feedback real-time
- Level filtering (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- Thread-safe (untuk future concurrent downloads)

Path log:
    Linux/macOS: ~/.local/share/mmpd/logs/mmpd.log
    Termux:      $PREFIX/var/log/mmpd/mmpd.log
    Windows:     %LOCALAPPDATA%/mmpd/logs/mmpd.log
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

from mmpd.config import get_config

# Konstanta
LOGGER_NAME = "mmpd"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB per file
BACKUP_COUNT = 5  # simpan 5 file rotation (total ~50 MB max)

# Format log untuk file (machine-parseable)
_FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
_FILE_DATE_FMT = "%Y-%m-%d %H:%M:%S"

# Format log untuk console (human-readable, singkat)
_CONSOLE_FORMAT = "%(levelname)s: %(message)s"

# Singleton state
_logger: Optional[logging.Logger] = None
_initialized = False


def setup_logging(
    level: int = logging.INFO,
    enable_console: bool = False,
    log_file: Optional[Path] = None,
) -> logging.Logger:
    """
    Setup logging mmpd.

    Args:
        level:           Log level (logging.DEBUG/INFO/WARNING/ERROR/CRITICAL)
        enable_console:  Tampilkan log di console juga (default False agar tidak
                         ganggu UI questionary/rich yang sudah ada)
        log_file:        Override path log file (untuk testing)

    Returns:
        Logger instance untuk `mmpd`
    """
    global _logger, _initialized

    if _initialized and log_file is None:
        return _logger or logging.getLogger(LOGGER_NAME)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False  # jangan bubble ke root logger

    # Hapus handler lama (jika re-init)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    # === File handler dengan rotation ===
    if log_file is None:
        config = get_config()
        try:
            config.ensure_dirs()
            log_file = config.log_dir / "mmpd.log"
        except Exception:
            # Fallback: log ke /tmp (Linux/macOS) atau %TEMP% (Windows)
            log_file = Path("/tmp") / "mmpd.log" if os.name != "nt" else Path(os.environ.get("TEMP", ".")) / "mmpd.log"

    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_FILE_DATE_FMT))
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # Jangan crash aplikasi kalau log file tidak bisa dibuat
        # (mis. Termux storage permission belum di-grant)
        # Fallback ke NullHandler agar logger.warning() tidak spam ke stderr
        logger.addHandler(logging.NullHandler())
        if enable_console:
            print(f"[logger] WARNING: tidak bisa menulis ke {log_file}: {e}")

    # === Console handler (opsional) ===
    if enable_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
        logger.addHandler(console_handler)

    _logger = logger
    _initialized = True

    logger.debug("Logging initialized: level=%s, log_file=%s", logging.getLevelName(level), log_file)
    return logger


def get_logger() -> logging.Logger:
    """
    Dapatkan logger `mmpd`. Auto-init dengan default (INFO, no console) jika
    belum di-setup. Memudahkan modul lain: tinggal `from mmpd.logger import get_logger; log = get_logger()`.
    """
    global _logger
    if _logger is None:
        _logger = setup_logging()
    return _logger


def get_log_file_path() -> Path:
    """Dapatkan path log file aktif (untuk `mmpd doctor`)."""
    config = get_config()
    return config.log_dir / "mmpd.log"
