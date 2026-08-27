"""
Filesystem helpers — atomic write, path sanitize, file operations.

Sebelum Fase 2.2, helper atomic write _atomic_write_text() tinggal di
downloader.py sebagai private function. Sekarang di-extract ke sini supaya:
- Bisa dipakai modul lain (lyrics.py, modes/*.py)
- Bisa di-unit-test terpisah
- Punya type hints lengkap
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional

from mmpd.logger import get_logger

_log = get_logger()


def atomic_write_text(path: str | Path, content: str, encoding: str = "utf-8") -> None:
    """
    Tulis file text secara atomik untuk mencegah korupsi saat crash mid-write.

    Pattern:
        1. Tulis content ke temporary file di direktori yang sama
        2. fsync() untuk flush ke disk
        3. os.replace() — atomic rename di POSIX & Windows

    Garansi:
        File `path` selalu utuh — versi lama ATAU versi baru, tidak pernah parsial.

    Args:
        path:     Target file path
        content:  Text content untuk ditulis
        encoding: Text encoding (default utf-8)

    Raises:
        OSError/IOError jika gagal (folder tidak writable, disk full, dll.)
    """
    path = str(path)
    dir_path = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".atomic_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        _log.debug("Atomic write OK: %s (%d bytes)", path, len(content))
    except Exception:
        # Bersihkan temporary file jika os.replace() gagal
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        _log.error("Atomic write FAILED: %s", path, exc_info=True)
        raise


def atomic_write_bytes(path: str | Path, data: bytes) -> None:
    """Versi bytes dari atomic_write_text — untuk binary file (thumbnail, etc.)."""
    path = str(path)
    dir_path = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dir_path, prefix=".atomic_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def find_audio_files(folder: str | Path, recursive: bool = True) -> List[Path]:
    """
    Cari semua file audio di folder. Format didukung: .mp3, .flac, .wav, .m4a.

    Args:
        folder:    Folder untuk di-scan
        recursive: True untuk scan subfolder juga

    Returns:
        List of Path ke file audio.
    """
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return []

    audio_extensions = {".mp3", ".flac", ".wav", ".m4a"}
    if recursive:
        return [p for p in folder_path.rglob("*") if p.suffix.lower() in audio_extensions and p.is_file()]
    return [p for p in folder_path.iterdir() if p.suffix.lower() in audio_extensions and p.is_file()]


def find_lyrics_files(folder: str | Path, recursive: bool = True) -> List[Path]:
    """Cari semua file lirik (.lrc) di folder."""
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return []

    if recursive:
        return [p for p in folder_path.rglob("*.lrc") if p.is_file()]
    return [p for p in folder_path.iterdir() if p.suffix.lower() == ".lrc" and p.is_file()]


def cleanup_temp_files(folder: str | Path, prefix: str = "temp_meta_") -> int:
    """
    Hapus file sampah sementara (mis. temp_meta_*) yang tertinggal dari
    eksekusi sebelumnya yang terputus.

    Args:
        folder:  Folder untuk dibersihkan
        prefix:  Prefix nama file sampah

    Returns:
        Jumlah file yang berhasil dihapus.
    """
    import glob

    pattern = str(Path(folder) / "**" / f"{prefix}*")
    junk_files = glob.glob(pattern, recursive=True)
    deleted = 0

    for junk in junk_files:
        try:
            os.remove(junk)
            deleted += 1
        except FileNotFoundError:
            pass  # race condition, OK
        except Exception as e:
            _log.warning("Gagal hapus %s: %s", junk, e)

    if deleted > 0:
        _log.info("Cleanup temp files: %d files removed", deleted)
    return deleted


def rename_lrc_with_lang_suffix(lrc_path: str | Path) -> Optional[str]:
    """
    Rename file LRC dengan suffix bahasa (mis. song.ja.lrc) ke nama bersih
    (song.lrc). Original yt-dlp output sering berformat .{lang}.lrc.

    Args:
        lrc_path: Path ke file .lrc yang mungkin punya suffix bahasa

    Returns:
        New path jika rename terjadi, None jika tidak perlu rename.
    """
    lrc_path = Path(lrc_path)
    name = lrc_path.name

    # Match pattern: name.{2-3 char lang}.lrc
    match = re.match(r"^(.+)\.([a-z]{2,3})\.lrc$", name, re.IGNORECASE)
    if not match:
        return None

    base_name = match.group(1)
    new_path = lrc_path.parent / f"{base_name}.lrc"

    if new_path.exists():
        # Sudah ada file dengan nama target — hapus yang suffix
        try:
            lrc_path.unlink()
            _log.debug("Removed duplicate LRC: %s", name)
            return None
        except Exception as e:
            _log.warning("Gagal hapus %s: %s", lrc_path, e)
            return None

    try:
        lrc_path.rename(new_path)
        _log.debug("Renamed LRC: %s → %s", name, new_path.name)
        return str(new_path)
    except Exception as e:
        _log.warning("Gagal rename %s: %s", lrc_path, e)
        return None


def ensure_dir(path: str | Path) -> Path:
    """Pastikan direktori ada, buat jika belum."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def safe_remove(path: str | Path, missing_ok: bool = True) -> bool:
    """Hapus file dengan aman, tanpa raise exception."""
    try:
        Path(path).unlink(missing_ok=missing_ok)
        return True
    except Exception as e:
        _log.warning("Gagal hapus %s: %s", path, e)
        return False
