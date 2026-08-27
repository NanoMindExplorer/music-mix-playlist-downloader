"""
Unit tests untuk mmpd.utils.fs — filesystem helpers.

Coverage:
    - atomic_write_text (basic write, overwrite, encoding)
    - atomic_write_bytes (binary data)
    - find_audio_files (mp3/flac/wav/m4a, recursive)
    - find_lyrics_files (.lrc, recursive)
    - cleanup_temp_files (hapus temp_meta_* pattern)
    - rename_lrc_with_lang_suffix (normalize .{lang}.lrc → .lrc)
    - ensure_dir, safe_remove
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mmpd.utils.fs import (
    atomic_write_bytes,
    atomic_write_text,
    cleanup_temp_files,
    ensure_dir,
    find_audio_files,
    find_lyrics_files,
    rename_lrc_with_lang_suffix,
    safe_remove,
)


# ============================================================================
# atomic_write_text
# ============================================================================

class TestAtomicWriteText:
    def test_basic_write(self, tmp_path: Path):
        """Test write ke file baru."""
        target = tmp_path / "test.txt"
        atomic_write_text(target, "Hello, World!")
        assert target.read_text(encoding="utf-8") == "Hello, World!"

    def test_overwrite_existing(self, tmp_path: Path):
        """Test overwrite file yang sudah ada."""
        target = tmp_path / "test.txt"
        target.write_text("old content", encoding="utf-8")
        atomic_write_text(target, "new content")
        assert target.read_text(encoding="utf-8") == "new content"

    def test_unicode_content(self, tmp_path: Path):
        """Test write content Unicode (CJK, emoji, dll)."""
        target = tmp_path / "unicode.txt"
        content = "こんにちは世界 🌍 مرحبا بالعالم"
        atomic_write_text(target, content)
        assert target.read_text(encoding="utf-8") == content

    def test_empty_content(self, tmp_path: Path):
        """Test write empty string."""
        target = tmp_path / "empty.txt"
        atomic_write_text(target, "")
        assert target.exists()
        assert target.read_text(encoding="utf-8") == ""

    def test_path_string_argument(self, tmp_path: Path):
        """Test accept Path atau string."""
        target_str = str(tmp_path / "str_path.txt")
        atomic_write_text(target_str, "content")
        assert Path(target_str).read_text(encoding="utf-8") == "content"

    def test_creates_parent_dir_does_not_exist(self, tmp_path: Path):
        """Atomic write ke file di direktori yang tidak ada harus raise."""
        target = tmp_path / "nonexistent_dir" / "test.txt"
        with pytest.raises(OSError):
            atomic_write_text(target, "content")

    def test_no_temp_file_left_after_success(self, tmp_path: Path):
        """Pastikan tidak ada file .atomic_*.tmp tersisa setelah write sukses."""
        target = tmp_path / "test.txt"
        atomic_write_text(target, "content")
        temp_files = list(tmp_path.glob(".atomic_*"))
        assert len(temp_files) == 0


# ============================================================================
# atomic_write_bytes
# ============================================================================

class TestAtomicWriteBytes:
    def test_binary_write(self, tmp_path: Path):
        """Test write binary data."""
        target = tmp_path / "thumb.jpg"
        data = b"\xff\xd8\xff\xe0\x00\x10JFIF"  # JPEG magic bytes
        atomic_write_bytes(target, data)
        assert target.read_bytes() == data

    def test_empty_bytes(self, tmp_path: Path):
        """Test write empty bytes."""
        target = tmp_path / "empty.bin"
        atomic_write_bytes(target, b"")
        assert target.exists()
        assert target.read_bytes() == b""


# ============================================================================
# find_audio_files
# ============================================================================

class TestFindAudioFiles:
    def test_find_mp3_files(self, tmp_path: Path):
        """Test cari .mp3 files."""
        (tmp_path / "song1.mp3").touch()
        (tmp_path / "song2.mp3").touch()
        (tmp_path / "readme.txt").touch()
        result = find_audio_files(tmp_path, recursive=False)
        assert len(result) == 2
        extensions = {p.suffix.lower() for p in result}
        assert extensions == {".mp3"}

    def test_find_multiple_formats(self, tmp_path: Path):
        """Test cari mp3, flac, wav, m4a."""
        for ext in [".mp3", ".flac", ".wav", ".m4a"]:
            (tmp_path / f"song{ext}").touch()
        result = find_audio_files(tmp_path, recursive=False)
        assert len(result) == 4

    def test_recursive_search(self, tmp_path: Path):
        """Test recursive cari di subfolder."""
        (tmp_path / "song1.mp3").touch()
        sub = tmp_path / "album"
        sub.mkdir()
        (sub / "song2.flac").touch()
        result = find_audio_files(tmp_path, recursive=True)
        assert len(result) == 2

    def test_non_recursive_search(self, tmp_path: Path):
        """Test non-recursive hanya scan root folder."""
        (tmp_path / "song1.mp3").touch()
        sub = tmp_path / "album"
        sub.mkdir()
        (sub / "song2.mp3").touch()
        result = find_audio_files(tmp_path, recursive=False)
        assert len(result) == 1

    def test_case_insensitive_extension(self, tmp_path: Path):
        """Test extension case insensitive (MP3 vs mp3)."""
        (tmp_path / "song.MP3").touch()
        (tmp_path / "song2.Flac").touch()
        result = find_audio_files(tmp_path, recursive=False)
        assert len(result) == 2

    def test_empty_directory(self, tmp_path: Path):
        """Test folder kosong return empty list."""
        result = find_audio_files(tmp_path, recursive=True)
        assert result == []

    def test_nonexistent_directory(self):
        """Test folder tidak ada return empty list."""
        result = find_audio_files("/nonexistent/path/xyz", recursive=True)
        assert result == []


# ============================================================================
# find_lyrics_files
# ============================================================================

class TestFindLyricsFiles:
    def test_find_lrc_files(self, tmp_path: Path):
        """Test cari .lrc files."""
        (tmp_path / "song1.lrc").touch()
        (tmp_path / "song2.lrc").touch()
        (tmp_path / "song1.mp3").touch()
        result = find_lyrics_files(tmp_path, recursive=False)
        assert len(result) == 2

    def test_recursive_lrc(self, tmp_path: Path):
        """Test recursive cari .lrc."""
        (tmp_path / "song1.lrc").touch()
        sub = tmp_path / "album"
        sub.mkdir()
        (sub / "song2.lrc").touch()
        result = find_lyrics_files(tmp_path, recursive=True)
        assert len(result) == 2


# ============================================================================
# cleanup_temp_files
# ============================================================================

class TestCleanupTempFiles:
    def test_cleanup_removes_temp_meta_files(self, tmp_path: Path):
        """Test hapus file dengan prefix temp_meta_."""
        (tmp_path / "temp_meta_song1.webp").touch()
        (tmp_path / "temp_meta_song2.jpg").touch()
        (tmp_path / "song1.mp3").touch()  # Tidak boleh terhapus
        (tmp_path / "song2.lrc").touch()

        deleted = cleanup_temp_files(tmp_path, prefix="temp_meta_")
        assert deleted == 2
        assert not (tmp_path / "temp_meta_song1.webp").exists()
        assert not (tmp_path / "temp_meta_song2.jpg").exists()
        assert (tmp_path / "song1.mp3").exists()
        assert (tmp_path / "song2.lrc").exists()

    def test_cleanup_recursive(self, tmp_path: Path):
        """Test hapus temp files di subfolder juga."""
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "temp_meta_x.webp").touch()
        (tmp_path / "temp_meta_y.jpg").touch()
        deleted = cleanup_temp_files(tmp_path)
        assert deleted == 2

    def test_cleanup_no_match(self, tmp_path: Path):
        """Test cleanup kalau tidak ada file match."""
        (tmp_path / "song.mp3").touch()
        deleted = cleanup_temp_files(tmp_path)
        assert deleted == 0

    def test_cleanup_empty_dir(self, tmp_path: Path):
        """Test cleanup folder kosong."""
        deleted = cleanup_temp_files(tmp_path)
        assert deleted == 0


# ============================================================================
# rename_lrc_with_lang_suffix
# ============================================================================

class TestRenameLrcWithLangSuffix:
    def test_rename_ja_suffix(self, tmp_path: Path):
        """Test rename song.ja.lrc → song.lrc."""
        old = tmp_path / "song.ja.lrc"
        old.write_text("lirik jepang", encoding="utf-8")
        new_path = rename_lrc_with_lang_suffix(old)
        assert new_path is not None
        assert Path(new_path).name == "song.lrc"
        assert not old.exists()
        assert Path(new_path).read_text(encoding="utf-8") == "lirik jepang"

    def test_rename_en_suffix(self, tmp_path: Path):
        """Test rename song.en.lrc → song.lrc."""
        old = tmp_path / "track.en.lrc"
        old.write_text("english lyrics", encoding="utf-8")
        new_path = rename_lrc_with_lang_suffix(old)
        assert new_path is not None
        assert Path(new_path).name == "track.lrc"

    def test_no_rename_for_clean_lrc(self, tmp_path: Path):
        """Test file .lrc tanpa suffix tidak di-rename."""
        clean = tmp_path / "song.lrc"
        clean.touch()
        result = rename_lrc_with_lang_suffix(clean)
        assert result is None
        assert clean.exists()

    def test_no_rename_for_long_lang_code(self, tmp_path: Path):
        """Test suffix lebih dari 3 char tidak di-rename."""
        # Pattern match: 2-3 char lang code only
        weird = tmp_path / "song.longer.lrc"
        weird.touch()
        result = rename_lrc_with_lang_suffix(weird)
        # 6 char "longer" tidak match pattern [a-z]{2,3}
        assert result is None


# ============================================================================
# ensure_dir, safe_remove
# ============================================================================

class TestEnsureDir:
    def test_create_single_dir(self, tmp_path: Path):
        """Test buat direktori baru."""
        target = tmp_path / "newdir"
        result = ensure_dir(target)
        assert result == target
        assert target.is_dir()

    def test_create_nested_dirs(self, tmp_path: Path):
        """Test buat nested directories."""
        target = tmp_path / "a" / "b" / "c"
        ensure_dir(target)
        assert target.is_dir()

    def test_idempotent(self, tmp_path: Path):
        """Test ensure_dir pada direktori yang sudah ada tidak raise."""
        target = tmp_path / "existing"
        target.mkdir()
        ensure_dir(target)  # Should not raise
        assert target.is_dir()


class TestSafeRemove:
    def test_remove_existing_file(self, tmp_path: Path):
        """Test hapus file yang ada."""
        f = tmp_path / "to_delete.txt"
        f.touch()
        assert safe_remove(f) is True
        assert not f.exists()

    def test_remove_nonexistent_with_missing_ok(self, tmp_path: Path):
        """Test hapus file tidak ada dengan missing_ok=True."""
        result = safe_remove(tmp_path / "nonexistent.txt", missing_ok=True)
        assert result is True

    def test_remove_nonexistent_without_missing_ok(self, tmp_path: Path):
        """Test hapus file tidak ada dengan missing_ok=False."""
        result = safe_remove(tmp_path / "nonexistent.txt", missing_ok=False)
        # safe_remove swallow exception, return False
        assert result is False
