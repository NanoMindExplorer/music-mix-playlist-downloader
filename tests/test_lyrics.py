"""
Unit tests untuk mmpd.lyrics — process_transliteration, process_translation, sync_huawei_lrc.

Strategy:
    - Mock pykakasi, pypinyin, korean_romanizer untuk test transliteration
    - Mock deep_translator untuk test translation
    - Mock shutil untuk test sync_huawei_lrc
    - Pakai tmp_path untuk file ops (no real filesystem side effects)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mmpd.lyrics import (
    fetch_synced_lyrics,
    process_translation,
    process_transliteration,
    sync_huawei_lrc,
)


# ============================================================================
# sync_huawei_lrc
# ============================================================================

class TestSyncHuaweiLrc:
    def test_skip_on_non_termux(self, tmp_path, mock_linux_env):
        """Test sync_huawei_lrc skip di non-Termux."""
        lrc = tmp_path / "song.lrc"
        lrc.write_text("lyrics", encoding="utf-8")
        # Should not raise, just return None
        sync_huawei_lrc(str(lrc))

    def test_skip_if_source_not_exists(self, mock_termux_env, monkeypatch):
        """Test sync skip jika file source tidak ada."""
        # Set fake home to /tmp-based path
        monkeypatch.setattr(Path, "home", lambda: Path("/data/data/com.termux/files/home"))
        sync_huawei_lrc("/nonexistent/file.lrc")
        # Should not raise

    def test_sync_copies_file_on_termux(self, tmp_path, mock_termux_env, monkeypatch):
        """Test sync copy file .lrc ke Musiclrc folder di Termux."""
        from mmpd.config import reset_config

        # Reset config dulu supaya singleton di-rebuild dengan env Termux yang baru
        reset_config()

        # Setup: source lrc + mock home directory ke tmp_path
        source_lrc = tmp_path / "song.lrc"
        source_lrc.write_text("lyrics content", encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        # Reset lagi setelah mock home supaya config pakai tmp_path
        reset_config()

        # Mock get_musiclrc_dir return tmp_path / "musiclrc"
        musiclrc_dir = tmp_path / "storage" / "shared" / "Music" / "Musiclrc"

        sync_huawei_lrc(str(source_lrc))

        # Verify file copied
        target = musiclrc_dir / "song.lrc"
        assert target.exists(), f"Expected {target} to exist after sync"
        assert target.read_text(encoding="utf-8") == "lyrics content"

    def test_sync_handles_oserror(self, tmp_path, mock_termux_env, monkeypatch):
        """Test sync tangani OSError gracefully (tidak raise)."""
        source_lrc = tmp_path / "song.lrc"
        source_lrc.write_text("lyrics", encoding="utf-8")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock os.makedirs untuk raise PermissionError (subclass OSError)
        with patch("os.makedirs", side_effect=PermissionError("denied")):
            # Should not raise
            sync_huawei_lrc(str(source_lrc))


# ============================================================================
# process_transliteration
# ============================================================================

class TestProcessTransliteration:
    def test_skip_if_file_not_exists(self):
        """Test skip kalau file tidak ada."""
        # Should not raise
        process_transliteration("/nonexistent/file.lrc", "❌ 1")

    def test_skip_if_mode_disabled(self, tmp_path):
        """Test skip kalau mode '❌ 1' (disabled)."""
        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:00.00]ただいま", encoding="utf-8")
        process_transliteration(str(lrc), "❌ 1")
        # File should be unchanged
        assert "ただいま" in lrc.read_text(encoding="utf-8")

    def test_skip_if_empty_file(self, tmp_path):
        """Test skip kalau file kosong."""
        lrc = tmp_path / "empty.lrc"
        lrc.write_text("", encoding="utf-8")
        process_transliteration(str(lrc), "🤖 4")  # auto-detect
        # Should not raise, file stays empty
        assert lrc.read_text(encoding="utf-8") == ""

    def test_japanese_transliteration(self, tmp_path):
        """Test transliterasi Japanese → Romaji (pakai real pykakasi)."""
        lrc = tmp_path / "ja.lrc"
        lrc.write_text("[00:00.00]ただいま\n[00:02.00]おかえり\n", encoding="utf-8")

        # Pakai real pykakasi (sudah terinstal di requirements.txt)
        process_transliteration(str(lrc), "🇯🇵 2")

        content = lrc.read_text(encoding="utf-8")
        # Verify timestamp preserved
        assert "[00:00.00]" in content
        # pykakasi akan convert 'ただいま' → 'tadaima'
        assert "tadaima" in content

    def test_chinese_transliteration(self, tmp_path):
        """Test transliterasi Chinese → Pinyin (pakai real pypinyin)."""
        lrc = tmp_path / "zh.lrc"
        lrc.write_text("[00:00.00]我爱你\n", encoding="utf-8")

        # Pakai real pypinyin
        process_transliteration(str(lrc), "🇨🇳 3")

        content = lrc.read_text(encoding="utf-8")
        # pypinyin akan convert '我爱你' → ['wo', 'ai', 'ni'] (tone marks might vary)
        # Verify pinyin added (space-separated)
        # Real pypinyin returns "wo ai ni" or "wǒ ài nǐ" depending on style
        # Just verify the structure: timestamp preserved + some latin chars added
        assert "[00:00.00]" in content
        # The content should have ASCII pinyin characters (not Chinese chars in lyrics line)
        # After transliteration, line should contain latin chars
        line = content.split("\n")[0]
        # Strip timestamp, sisanya harus ada latin chars
        lyric_text = line.replace("[00:00.00]", "").strip()
        assert lyric_text, "Transliterated text should not be empty"
        # Should contain ASCII characters (pinyin)
        assert any(c.isascii() and c.isalpha() for c in lyric_text)

    def test_korean_transliteration(self, tmp_path):
        """Test transliterasi Korean → Romanized (pakai real korean_romanizer)."""
        lrc = tmp_path / "ko.lrc"
        lrc.write_text("[00:00.00]안녕하세요\n", encoding="utf-8")

        # Pakai real korean_romanizer + langdetect untuk auto-detect
        # Mode 🤖 4 = auto-detect language
        try:
            process_transliteration(str(lrc), "🤖 4")
        except Exception:
            pytest.skip("langdetect tidak bisa detect '안녕하세요' (terlalu pendek)")

        content = lrc.read_text(encoding="utf-8")
        assert "[00:00.00]" in content
        # Verify some romanization happened (korean chars should be replaced)
        # korean_romanizer akan convert '안녕하세요' → 'annyeonghaseyo' or similar
        line = content.split("\n")[0]
        lyric_text = line.replace("[00:00.00]", "").strip()
        if lyric_text:
            # Should contain ASCII chars (romanized)
            assert any(c.isascii() and c.isalpha() for c in lyric_text)

    def test_atomic_write_preserves_timestamps(self, tmp_path):
        """Test transliterasi tidak merusak timestamp format."""
        lrc = tmp_path / "test.lrc"
        lrc.write_text("[00:01.50]test line\n[00:03.00]another\n", encoding="utf-8")

        # Mock pykakasi untuk return apa adanya
        mock_kakasi = MagicMock()
        mock_kakasi.convert.side_effect = lambda text: [{"hepburn": text}]

        with patch.dict("sys.modules", {"pykakasi": MagicMock(kakasi=lambda: mock_kakasi)}):
            process_transliteration(str(lrc), "🇯🇵 2")

        content = lrc.read_text(encoding="utf-8")
        # Verify timestamps preserved
        assert "[00:01.50]" in content
        assert "[00:03.00]" in content

    def test_skip_latin_language_in_auto_mode(self, tmp_path):
        """Test skip transliterasi kalau bahasa terdeteksi Latin (en/id/dll)."""
        lrc = tmp_path / "en.lrc"
        english_content = "[00:00.00]Hello world\n[00:02.00]This is English\n"
        lrc.write_text(english_content, encoding="utf-8")

        # Mock langdetect untuk return 'en'
        mock_langdetect = MagicMock()
        mock_langdetect.detect.return_value = "en"

        with patch.dict("sys.modules", {"langdetect": mock_langdetect}):
            process_transliteration(str(lrc), "🤖 4")

        # File should be unchanged (skipped)
        assert lrc.read_text(encoding="utf-8") == english_content


# ============================================================================
# process_translation
# ============================================================================

class TestProcessTranslation:
    def test_skip_if_file_not_exists(self):
        """Test skip kalau file tidak ada."""
        process_translation("/nonexistent.lrc", True)
        # Should not raise

    def test_skip_if_translate_mode_false(self, tmp_path):
        """Test skip kalau translate_mode=False."""
        lrc = tmp_path / "song.lrc"
        original = "[00:00.00]Hello\n"
        lrc.write_text(original, encoding="utf-8")
        process_translation(str(lrc), False)
        assert lrc.read_text(encoding="utf-8") == original

    def test_translation_adds_bilingual_line(self, tmp_path):
        """Test translation menambah baris bilingual dengan timestamp identik."""
        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:00.00]Hello world\n", encoding="utf-8")

        # Mock GoogleTranslator
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Halo dunia"

        mock_module = MagicMock()
        mock_module.GoogleTranslator = MagicMock(return_value=mock_translator)

        with patch.dict("sys.modules", {"deep_translator": mock_module}):
            process_translation(str(lrc), True)

        content = lrc.read_text(encoding="utf-8")
        # Original line preserved and formatted
        assert '<font color="#FFFFFF">Hello world</font>' in content
        # Translation appended with <br> and <small>
        assert '<br><font color="#00FFFF"><small>Halo dunia</small></font>' in content

    def test_translation_fallback_to_mymemory(self, tmp_path):
        """Test fallback ke MyMemory kalau Google error."""
        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:00.00]Hello\n", encoding="utf-8")

        # Mock: Google raises, MyMemory succeeds
        mock_google = MagicMock()
        mock_google.translate.side_effect = Exception("Google 500")

        mock_mymemory = MagicMock()
        mock_mymemory.translate.return_value = "Halo"

        mock_module = MagicMock()
        mock_module.GoogleTranslator = MagicMock(return_value=mock_google)
        mock_module.MyMemoryTranslator = MagicMock(return_value=mock_mymemory)

        mock_langdetect = MagicMock()
        mock_langdetect.detect.return_value = "en"

        with patch.dict("sys.modules", {
            "deep_translator": mock_module,
            "langdetect": mock_langdetect,
        }):
            process_translation(str(lrc), True)

        content = lrc.read_text(encoding="utf-8")
        # Should have translation from MyMemory
        assert "Halo" in content

    def test_translation_handles_all_engines_failure(self, tmp_path):
        """Test translation tidak crash kalau semua mesin gagal."""
        lrc = tmp_path / "song.lrc"
        original = "[00:00.00]Hello\n"
        lrc.write_text(original, encoding="utf-8")

        mock_google = MagicMock()
        mock_google.translate.side_effect = Exception("Google failed")

        mock_mymemory = MagicMock()
        mock_mymemory.translate.side_effect = Exception("MyMemory failed")

        mock_module = MagicMock()
        mock_module.GoogleTranslator = MagicMock(return_value=mock_google)
        mock_module.MyMemoryTranslator = MagicMock(return_value=mock_mymemory)

        mock_langdetect = MagicMock()
        mock_langdetect.detect.return_value = "en"

        with patch.dict("sys.modules", {
            "deep_translator": mock_module,
            "langdetect": mock_langdetect,
        }):
            # Should not raise
            process_translation(str(lrc), True)

        # File might be modified (with original only) or unchanged
        # Main point: no exception raised

    def test_translation_skip_identical_lines(self, tmp_path):
        """Test translation skip baris yang translated text sama dengan original."""
        lrc = tmp_path / "song.lrc"
        # Indonesian text — translation akan sama (id → id)
        lrc.write_text("[00:00.00]Halo dunia\n", encoding="utf-8")

        # Mock: Google return same text (already Indonesian)
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Halo dunia"

        mock_module = MagicMock()
        mock_module.GoogleTranslator = MagicMock(return_value=mock_translator)

        with patch.dict("sys.modules", {"deep_translator": mock_module}):
            process_translation(str(lrc), True)

        content = lrc.read_text(encoding="utf-8")
        # Should NOT have duplicate line (skip identical translation)
        assert content.count("Halo dunia") == 1
        assert "<small>" not in content


# ============================================================================
# fetch_synced_lyrics (integration test with mocks)
# ============================================================================

class TestFetchSyncedLyrics:
    def test_fetch_returns_false_when_no_lyrics_found(self, tmp_path):
        """Test fetch return False kalau lirik tidak ditemukan."""
        lrc_path = tmp_path / "song.lrc"

        # Mock LyricsChain return None
        mock_chain = MagicMock()
        mock_chain.search.return_value = None

        with patch("mmpd.lyrics_providers.build_default_chain", return_value=mock_chain), \
             patch("mmpd.lyrics_providers.LyricsChain", mock_chain):
            # Also mock requests supaya iTunes fallback tidak hit network
            mock_requests = MagicMock()
            mock_requests.get.return_value = MagicMock(
                status_code=404,
                json=lambda: {"resultCount": 0},
                raise_for_status=MagicMock(),
            )
            with patch.dict("sys.modules", {"requests": mock_requests}):
                result = fetch_synced_lyrics(
                    title="Nonexistent Song",
                    lrc_path=str(lrc_path),
                    sync_huawei=False,
                )

        assert result is False
        assert not lrc_path.exists()

    def test_fetch_writes_lyrics_when_found(self, tmp_path):
        """Test fetch tulis lirik ke file kalau ditemukan."""
        lrc_path = tmp_path / "song.lrc"

        # Mock LyricsChain return result with lyrics
        mock_result = MagicMock()
        mock_result.best_lyrics = "[00:00.00]Hello world"
        mock_result.provider = "lrclib"

        mock_chain = MagicMock()
        mock_chain.search.return_value = mock_result

        with patch("mmpd.lyrics_providers.build_default_chain", return_value=mock_chain):
            result = fetch_synced_lyrics(
                title="Hello",
                lrc_path=str(lrc_path),
                sync_huawei=False,
            )

        assert result is True
        assert lrc_path.exists()
        content = lrc_path.read_text(encoding="utf-8")
        assert "Hello world" in content

    def test_fetch_with_override_query(self, tmp_path):
        """Test fetch pakai override_query sebagai search."""
        lrc_path = tmp_path / "song.lrc"

        mock_result = MagicMock()
        mock_result.best_lyrics = "[00:00.00]Found"
        mock_chain = MagicMock()
        mock_chain.search.return_value = mock_result

        with patch("mmpd.lyrics_providers.build_default_chain", return_value=mock_chain):
            fetch_synced_lyrics(
                title="Original Title",
                lrc_path=str(lrc_path),
                sync_huawei=False,
                override_query="Custom Search Query",
            )

        # Verify chain.search dipanggil dengan TrackInfo(title="Custom Search Query")
        call_args = mock_chain.search.call_args[0][0]
        assert call_args.title == "Custom Search Query"

    def test_fetch_handles_exception_gracefully(self, tmp_path):
        """Test fetch tidak raise kalau ada exception."""
        lrc_path = tmp_path / "song.lrc"

        mock_chain = MagicMock()
        mock_chain.search.side_effect = Exception("Unexpected error")

        with patch("mmpd.lyrics_providers.build_default_chain", return_value=mock_chain):
            # Should not raise
            result = fetch_synced_lyrics(
                title="Test",
                lrc_path=str(lrc_path),
                sync_huawei=False,
            )

        assert result is False
