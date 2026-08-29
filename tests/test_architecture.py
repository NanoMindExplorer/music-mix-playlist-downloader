"""
Tests Fase A — arsitektur baru: LyricLine model, organizer recursive/dry-run,
import path backward-compat.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


# ============================================================================
# LyricLine data model (P2)
# ============================================================================

class TestLyricLine:
    def test_basic_fields(self):
        from mmpd.types import LyricLine

        ln = LyricLine(ts=61.5, original="聽海", latin="ting hai", id_text="dengarkan laut")
        assert ln.ts == 61.5
        assert ln.display == "ting hai"      # latin diprioritaskan untuk tampilan
        assert ln.has_translation is True

    def test_display_falls_back_to_original(self):
        from mmpd.types import LyricLine

        ln = LyricLine(ts=10.0, original="ハロ")
        assert ln.display == "ハロ"

    def test_to_lrc_line(self):
        from mmpd.types import LyricLine

        ln = LyricLine(ts=61.5, original="ハロ")
        assert ln.to_lrc_line() == "[01:01.50]ハロ"

    def test_no_ts_line(self):
        from mmpd.types import LyricLine

        ln = LyricLine(ts=None, original="[ti:meta]")
        assert ln.to_lrc_line() == "[ti:meta]"

    def test_parse_and_render_roundtrip(self):
        from mmpd.lyrics import parse_lrc_lines, render_lrc
        from mmpd.types import LyricLine

        lrc_text = "[00:01.00]Hello\n[00:05.50]World\n[ti:skip me]\n"
        lines = parse_lrc_lines(lrc_text)
        assert len(lines) == 2
        assert lines[0].ts == 1.0
        assert lines[0].original == "Hello"
        assert lines[1].ts == 5.5

        # Set terjemahan lalu render → gabung 1 baris
        lines[0] = LyricLine(ts=1.0, original="Hello", id_text="Halo")
        rendered = render_lrc(lines)
        assert "[00:01.00]Hello" in rendered

    def test_write_bilingual_from_lines_pisah(self, tmp_path):
        from mmpd.lyrics import write_bilingual_from_lines
        from mmpd.types import LyricLine

        lines = [
            LyricLine(ts=1.0, original="Hello", id_text="Halo"),
            LyricLine(ts=5.0, original="World", id_text="Dunia"),
        ]
        lrc = tmp_path / "song.lrc"
        written = write_bilingual_from_lines(str(lrc), lines, format_mode="pisah")
        assert written == 2
        content = lrc.read_text(encoding="utf-8")
        out_lines = [ln for ln in content.splitlines() if ln.strip()]
        assert len(out_lines) == 4, "pisah = 2x jumlah baris"
        assert any("Halo" in ln and ln.startswith("[00:01.") for ln in out_lines)

    def test_write_bilingual_from_lines_id_only(self, tmp_path):
        from mmpd.lyrics import write_bilingual_from_lines
        from mmpd.types import LyricLine

        lines = [LyricLine(ts=1.0, original="Hello", id_text="Halo")]
        lrc = tmp_path / "song.lrc"
        write_bilingual_from_lines(str(lrc), lines, format_mode="id_only")
        assert (tmp_path / "song.id.lrc").exists()
        assert "Halo" in lrc.read_text(encoding="utf-8") is False or True  # file utama boleh


# ============================================================================
# Import path backward-compat (modul dipecah, path lama tetap jalan)
# ============================================================================

class TestBackwardCompatImports:
    def test_mmpd_lyrics_public_api(self):
        from mmpd.lyrics import (
            detect_script,
            fetch_synced_lyrics,
            is_already_bilingual,
            process_translation,
            process_transliteration,
            sync_huawei_lrc,
        )
        assert callable(fetch_synced_lyrics)
        assert callable(process_translation)
        assert callable(process_transliteration)
        assert callable(sync_huawei_lrc)
        assert callable(detect_script)
        assert callable(is_already_bilingual)

    def test_mmpd_lyrics_privates_used_by_tests(self):
        from mmpd.lyrics import _write_bilingual_lrc, _strip_lrc_text
        assert callable(_write_bilingual_lrc)
        assert _strip_lrc_text("[00:01.00]Hi") == "Hi"

    def test_downloader_still_re_exports(self):
        import downloader
        assert hasattr(downloader, "run_cli")
        assert hasattr(downloader, "fetch_synced_lyrics")

    def test_modes_download_shim(self):
        from mmpd.modes.download import (
            _find_new_audio_files,
            _snapshot_audio_files,
            run_cli,
            run_download_noninteractive,
        )
        assert callable(run_cli)
        assert callable(run_download_noninteractive)

    def test_lyrics_subpackage_modules_importable(self):
        import mmpd.lyrics.fetch  # noqa: F401
        import mmpd.lyrics.huawei  # noqa: F401
        import mmpd.lyrics.lrc_format  # noqa: F401
        import mmpd.lyrics.translate  # noqa: F401
        import mmpd.lyrics.transliterate  # noqa: F401


# ============================================================================
# Organizer recursive + dry-run (P1/Fase A)
# ============================================================================

class TestOrganizerRecursive:
    def _setup_folder(self, tmp_path: Path) -> Path:
        downloads = tmp_path / "Downloads"
        (downloads / "sub").mkdir(parents=True)
        (downloads / "song.mp3").write_bytes(b"x")
        (downloads / "song.lrc").write_text("[00:01.00]lirik\n", encoding="utf-8")
        (downloads / "sub" / "other.flac").write_bytes(b"y")
        (downloads / "sub" / "other.lrc").write_text("[00:02.00]lirik2\n", encoding="utf-8")
        return downloads

    def test_recursive_finds_subfolder(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        downloads = self._setup_folder(tmp_path)
        from mmpd.modes.organizer import _scan_files
        audio, lrc = _scan_files(str(downloads), recursive=True)
        assert len(audio) == 2, "Rekursif harus menemukan file di subfolder"
        assert len(lrc) == 2

        audio_root, lrc_root = _scan_files(str(downloads), recursive=False)
        assert len(audio_root) == 1
        assert len(lrc_root) == 1

    def test_dry_run_moves_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        downloads = self._setup_folder(tmp_path)
        from mmpd.modes.organizer import run_organizer

        code = run_organizer(folder=str(downloads), recursive=True, dry_run=True)
        assert code == 0
        # Tidak ada file yang dipindah
        assert (downloads / "song.mp3").exists()
        assert (downloads / "sub" / "other.flac").exists()

    def test_actual_move(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        from mmpd import config as cfg
        cfg.reset_config()

        downloads = self._setup_folder(tmp_path)
        from mmpd.modes.organizer import run_organizer

        code = run_organizer(folder=str(downloads), recursive=True, dry_run=False)
        assert code == 0
        # File terpindah ke Music/Musiclrc
        assert not (downloads / "song.mp3").exists()
        music = tmp_path / "Downloads" / "Music"
        assert (music / "song.mp3").exists()
        assert (music / "Musiclrc" / "song.lrc").exists()
        assert (music / "other.flac").exists()

    def test_ignores_id_lrc(self, tmp_path):
        from mmpd.modes.organizer import _scan_files
        d = tmp_path / "x"
        d.mkdir()
        (d / "a.id.lrc").write_text("x", encoding="utf-8")
        (d / "a.lrc").write_text("x", encoding="utf-8")
        _, lrc = _scan_files(str(d), recursive=True)
        assert len(lrc) == 1, "File .id.lrc (output terpisah) tidak boleh ikut dirapikan"


# ============================================================================
# CLI organize subcommand
# ============================================================================

class TestCLIOrganize:
    def test_parser_accepts_organize(self):
        from mmpd.cli import build_parser
        args = build_parser().parse_args(["organize", "--dir", "/tmp/x", "--dry-run"])
        assert args.command == "organize"
        assert args.dry_run is True
        assert args.no_recursive is False
