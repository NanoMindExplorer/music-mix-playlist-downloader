"""
Regression tests Fase L — pipeline lirik lagu Asia (fixtures .lrc asli).

Fixture menutupi 5 kasus nyata dari koleksi user (79 lagu, campuran
Cina/Taiwan/Thailand/cover/Jepang):
    jiangnan_zh.lrc       — Mandarin simplified+traditional mix (林俊杰)
    tinghai_zh_tw.lrc     — Traditional Chinese penuh (張惠妹) → OpenCC t2s
    ping_th.lrc           — Thai script (กัน นภัทร)
    flukie_cover_th.lrc   — lagu COVER (judul mengandung penanda cover)
    yorunikakeru_ja.lrc   — Japanese kana+kanji (YOASOBI)

Yang dijaga (JANGAN sampai rusak oleh refactor):
    1. Timestamp [mm:ss.xx] tidak pernah rusak oleh transliterasi
    2. Terjemahan SELALU dari aksara asli (snapshot), bukan pinyin/romaji
    3. TrackInfo.clean_search_query == matching.normalize_track_query (satu sumber)
    4. Format bilingual gabung/pisah/id_only menghasilkan LRC valid
    5. Negative cache terpisah dari lyrics_cache utama
    6. USLT/SYLT embedding membaca LRC dengan benar
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture_lrc(tmp_path: Path):
    """Copy fixture .lrc ke tmp_path, return path copy."""
    def _copy(name: str) -> Path:
        src = FIXTURES / name
        dst = tmp_path / name
        shutil.copy2(src, dst)
        return dst
    return _copy


# ============================================================================
# 1. normalize_track_query — satu sumber kebenaran
# ============================================================================

class TestNormalizeTrackQuery:
    def test_trackinfo_delegates_to_normalize(self):
        """TrackInfo.clean_search_query HARUS sama dengan matching.normalize_track_query."""
        from mmpd.types import TrackInfo
        from mmpd.utils.matching import normalize_track_query

        cases = [
            ("JUSTadICE (Official Music Video)", "Rainych"),
            ("聽海", "張惠妹"),
            ("เสียงจากลูกชาย COVER", "FLUKIE"),
            ("夜に駆ける [Official MV]", "YOASOBI"),
        ]
        for title, artist in cases:
            track = TrackInfo(title=title, artist=artist)
            assert track.clean_search_query() == normalize_track_query(title, artist), (
                f"Query mismatch untuk {title!r} — dua implementasi normalisasi "
                f"tidak sinkron lagi (regresi P0/Fase L)"
            )

    def test_promo_keywords_removed(self):
        from mmpd.utils.matching import normalize_track_query
        assert "official" not in normalize_track_query("Hello (Official Music Video)").lower()
        assert "cover" not in normalize_track_query("Song COVER").lower()
        assert "翻唱" not in normalize_track_query("歌曲 翻唱")

    def test_brackets_removed(self):
        from mmpd.utils.matching import normalize_track_query
        assert normalize_track_query("Title 【東方】") == "Title"

    def test_artist_prepended(self):
        from mmpd.utils.matching import normalize_track_query
        q = normalize_track_query("Hello", "Adele")
        assert q.startswith("Adele")
        assert q.endswith("Hello")

    def test_traditional_to_simplified(self):
        from mmpd.utils.matching import normalize_track_query
        q = normalize_track_query("聽海")
        assert "聽" not in q  # harus sudah t2s → 听

    def test_empty_title(self):
        from mmpd.utils.matching import normalize_track_query
        assert normalize_track_query("") == ""
        assert normalize_track_query(None) == ""  # type: ignore[arg-type]


# ============================================================================
# 2. Transliterasi tidak merusak timestamp + return snapshot
# ============================================================================

class TestTransliterationFixtures:
    @pytest.mark.parametrize("fixture,mode", [
        ("jiangnan_zh.lrc", "🇨🇳 3"),
        ("tinghai_zh_tw.lrc", "🇨🇳 3"),
        ("yorunikakeru_ja.lrc", "🇯🇵 2"),
        ("flukie_cover_th.lrc", "🤖 5"),
    ])
    def test_timestamps_survive(self, fixture_lrc, fixture, mode):
        """Semua timestamp asli harus tetap ada setelah transliterasi."""
        from mmpd.lyrics import process_transliteration

        lrc = fixture_lrc(fixture)
        before = [
            ln for ln in lrc.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("[0") or ln.strip().startswith("[1")
        ]
        process_transliteration(str(lrc), mode)
        after_text = lrc.read_text(encoding="utf-8")

        for ts_line in before:
            ts = ts_line.split("]")[0] + "]"
            assert ts in after_text, f"Timestamp {ts} hilang setelah transliterasi!"

    def test_snapshot_returned(self, fixture_lrc):
        """process_transliteration mengembalikan baris ASLI (aksara asli)."""
        from mmpd.lyrics import process_transliteration

        lrc = fixture_lrc("yorunikakeru_ja.lrc")
        original_text = lrc.read_text(encoding="utf-8")
        snapshot = process_transliteration(str(lrc), "🇯🇵 2")

        assert snapshot is not None, "Snapshot asli harus dikembalikan (Fase L contract)"
        # Snapshot berisi aksara Jepang asli, BUKAN romaji
        joined = "".join(snapshot)
        assert "沈む" in joined, "Snapshot harus berisi aksara asli, bukan hasil latin"
        # File hasil sudah di-latin-kan
        new_text = lrc.read_text(encoding="utf-8")
        assert new_text != original_text

    def test_skip_mode_returns_none(self, fixture_lrc):
        from mmpd.lyrics import process_transliteration
        lrc = fixture_lrc("jiangnan_zh.lrc")
        assert process_transliteration(str(lrc), "❌ 1") is None

    def test_thai_fixture_handled_by_auto(self, fixture_lrc):
        """Fixture Thai tidak crash dengan mode auto (fallback anyascii/pythainlp)."""
        from mmpd.lyrics import process_transliteration
        lrc = fixture_lrc("ping_th.lrc")
        process_transliteration(str(lrc), "🤖 5")  # tidak boleh raise
        assert lrc.exists()

    def test_jyutping_mode_no_crash(self, fixture_lrc):
        """Mode Kanton (Jyutping) tidak crash walau teksnya Mandarin."""
        from mmpd.lyrics import process_transliteration
        lrc = fixture_lrc("jiangnan_zh.lrc")
        process_transliteration(str(lrc), "🇭🇰 4")  # tidak boleh raise
        assert lrc.exists()


# ============================================================================
# 3. Deteksi bilingual
# ============================================================================

class TestBilingualDetection:
    def test_raw_fixture_not_bilingual(self, fixture_lrc):
        from mmpd.lyrics import is_already_bilingual
        lines = (FIXTURES / "jiangnan_zh.lrc").read_text(encoding="utf-8").splitlines(keepends=True)
        assert not is_already_bilingual(lines)

    def test_gabung_format_detected_as_bilingual(self):
        from mmpd.lyrics import is_already_bilingual
        lines = [
            "[00:01.00]Hello world  /  Halo dunia\n",
            "[00:05.00]Second line  /  Baris kedua\n",
            "[00:09.00]Third  /  Ketiga\n",
        ]
        assert is_already_bilingual(lines)

    def test_pisah_format_detected_as_bilingual(self):
        from mmpd.lyrics import is_already_bilingual
        lines = [
            "[00:01.00]Hello world\n",
            "[00:01.40]Halo dunia\n",
            "[00:05.00]Second line\n",
            "[00:05.40]Baris kedua\n",
            "[00:09.00]Third\n",
            "[00:09.40]Ketiga\n",
        ]
        assert is_already_bilingual(lines)


# ============================================================================
# 4. Format LRC bilingual (gabung / pisah / id_only)
# ============================================================================

class TestBilingualFormats:
    def _write_bilingual(self, tmp_path, fmt):
        from mmpd.lyrics import _write_bilingual_lrc

        lrc = tmp_path / "song.lrc"
        lrc.write_text(
            "[00:01.00]Hello world\n[00:05.00]Second line\n",
            encoding="utf-8",
        )
        os.environ["MMPD_BILINGUAL_FORMAT"] = fmt
        try:
            _write_bilingual_lrc(
                str(lrc),
                ["[00:01.00]Hello world\n", "[00:05.00]Second line\n"],
                ["Hello world", "Second line"],
                ["Halo dunia", "Baris kedua"],
            )
        finally:
            os.environ.pop("MMPD_BILINGUAL_FORMAT", None)
        return lrc

    def test_gabung_single_line(self, tmp_path):
        lrc = self._write_bilingual(tmp_path, "gabung")
        content = lrc.read_text(encoding="utf-8")
        assert "  /  " in content, "Format gabung harus pakai pemisah '  /  '"
        assert "[00:01.00]" in content

    def test_pisah_micro_offset(self, tmp_path):
        lrc = self._write_bilingual(tmp_path, "pisah")
        content = lrc.read_text(encoding="utf-8")
        lines = [ln for ln in content.splitlines() if ln.strip()]
        assert len(lines) == 4, "Format pisah harus menggandakan jumlah baris"
        # Baris terjemahan punya micro-offset (bukan timestamp identik)
        assert any(ln.startswith("[00:01.") and "Halo dunia" in ln for ln in lines)
        offsets = [ln.split("]")[0] for ln in lines]
        assert offsets[0] != offsets[1], "pisah: offset terjemahan harus beda"

    def test_id_only_separate_file(self, tmp_path):
        lrc = self._write_bilingual(tmp_path, "id_only")
        id_lrc = tmp_path / "song.id.lrc"
        assert id_lrc.exists(), "Format id_only harus membuat file .id.lrc terpisah"
        id_content = id_lrc.read_text(encoding="utf-8")
        assert "Halo dunia" in id_content
        main_content = lrc.read_text(encoding="utf-8")
        assert "Halo dunia" not in main_content, "id_only: file utama tetap asli"


# ============================================================================
# 5. Negative cache — terpisah dari cache utama
# ============================================================================

class TestNegativeCache:
    def test_not_found_never_pollutes_main_cache(self):
        from mmpd import cache

        cache.set_lyrics_not_found("Lagu Ngalor Ngidul", artist="X")
        assert cache.is_lyrics_known_missing("Lagu Ngalor Ngidul", artist="X")
        # PENTING: entry negative TIDAK boleh muncul sebagai lyrics_cache hit
        assert cache.get_lyrics_cache("Lagu Ngalor Ngidul", artist="X") is None

    def test_negative_expires(self, monkeypatch):
        from mmpd import cache
        import time as _time

        cache.set_lyrics_not_found("Song Expired", ttl_seconds=1)
        # Geser waktu 2 detik ke depan
        real_time = _time.time
        monkeypatch.setattr(_time, "time", lambda: real_time() + 2)
        assert not cache.is_lyrics_known_missing("Song Expired")

    def test_negative_isolated_per_track(self):
        from mmpd import cache
        cache.set_lyrics_not_found("Track A", artist="Art")
        assert not cache.is_lyrics_known_missing("Track B", artist="Art")

    def test_clear_negative_cache(self):
        from mmpd import cache
        cache.set_lyrics_not_found("Track C")
        assert cache.clear_negative_cache() >= 1
        assert not cache.is_lyrics_known_missing("Track C")


# ============================================================================
# 6. LyricsChain → negative cache integration
# ============================================================================

class TestChainNegativeCacheIntegration:
    def test_chain_sets_negative_on_total_miss(self):
        """Semua provider gagal → negative cache terisi → run kedua instant None."""
        from mmpd import cache
        from mmpd.lyrics_providers import LyricsChain
        from mmpd.types import TrackInfo

        class NullProvider:
            name = "null"
            priority = 0
            def search(self, track):
                return None

        chain = LyricsChain([NullProvider()])
        track = TrackInfo(title="Lagu Tidak Ada Di Mana Mana")
        assert chain.search(track) is None
        assert cache.is_lyrics_known_missing(track.title) is True, (
            "Total miss harus mengisi negative cache (Fase L)"
        )
        # Run kedua: instant None tanpa panggil provider lagi
        calls = {"n": 0}

        class CountingNull(NullProvider):
            def search(self, track):
                calls["n"] += 1
                return None

        chain2 = LyricsChain([CountingNull()])
        assert chain2.search(track) is None
        assert calls["n"] == 0, "Negative cache hit harus skip provider call"


# ============================================================================
# 7. ID3 USLT/SYLT embedding
# ============================================================================

class TestId3Embed:
    def test_parse_lrc_to_lines_sorted(self):
        from mmpd.id3_embed import parse_lrc_to_lines
        lrc = "[00:10.00]b\n[00:05.00]a\n[00:20.00]c\n"
        lines = parse_lrc_to_lines(lrc)
        assert [t for t, _ in lines] == [5.0, 10.0, 20.0]
        assert [x for _, x in lines] == ["a", "b", "c"]

    def test_lrc_to_plain_strips_timestamps(self):
        from mmpd.id3_embed import _lrc_to_plain
        plain = _lrc_to_plain("[00:01.00]Hello\n[ti:meta]\n[00:05.00]World\n")
        assert plain == "Hello\nWorld"

    def test_embed_uslt_sylt_to_mp3(self, tmp_path):
        """Embed USLT+SYLT ke MP3 sungguhan lalu baca balik."""
        pytest.importorskip("mutagen")
        from mutagen.id3 import ID3
        from mmpd.id3_embed import embed_lyrics_to_audio, has_embedded_lyrics

        # Buat MP3 minimal (ID3 tag saja tanpa audio frame — cukup untuk test tag)
        mp3 = tmp_path / "song.mp3"
        ID3().save(str(mp3))
        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:01.00]Hello world\n[00:05.00]Halo dunia\n", encoding="utf-8")

        assert embed_lyrics_to_audio(str(mp3), str(lrc)) is True
        assert has_embedded_lyrics(str(mp3)) is True

        tags = ID3(str(mp3))
        uslt = tags.getall("USLT")
        sylt = tags.getall("SYLT")
        assert uslt and "Hello world" in uslt[0].text
        assert sylt, "SYLT (synced) harus ikut ditanam untuk MP3"
        # mutagen menyimpan SYLT.text sebagai list of (teks, waktu_ms)
        sylt_texts = [t for t, _ in sylt[0].text]
        assert "Hello world" in sylt_texts

    def test_embed_flac_vorbis(self, tmp_path):
        pytest.importorskip("mutagen")
        from mutagen.flac import FLAC
        from mmpd.id3_embed import embed_lyrics_to_audio, has_embedded_lyrics

        # Buat FLAC minimal valid (magic + STREAMINFO dengan sample rate valid)
        flac = tmp_path / "song.flac"
        streaminfo = bytearray(34)
        streaminfo[0:2] = (0x1000).to_bytes(2, "big")   # min block size
        streaminfo[2:4] = (0x1000).to_bytes(2, "big")   # max block size
        # sample_rate=44100, channels=2, bits=16, total_samples=0 (packed 8 byte)
        packed = (44100 << 44) | (1 << 41) | (15 << 36) | 0
        streaminfo[10:18] = packed.to_bytes(8, "big")
        with open(flac, "wb") as f:
            f.write(b"fLaC")
            f.write(bytes([0x80, 0x00, 0x00, 0x22]))  # last block, STREAMINFO, len 34
            f.write(bytes(streaminfo))

        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:01.00]Hello\n", encoding="utf-8")

        assert embed_lyrics_to_audio(str(flac), str(lrc)) is True
        assert has_embedded_lyrics(str(flac)) is True
        audio = FLAC(str(flac))
        assert "Hello" in (audio.get("LYRICS") or [""])[0]
        assert "[00:01.00]" in (audio.get("SYNCEDLYRICS") or [""])[0]

    def test_no_overwrite_flag(self, tmp_path):
        pytest.importorskip("mutagen")
        from mutagen.id3 import ID3
        from mmpd.id3_embed import embed_lyrics_to_audio

        mp3 = tmp_path / "song.mp3"
        ID3().save(str(mp3))
        lrc = tmp_path / "song.lrc"
        lrc.write_text("[00:01.00]Hello\n", encoding="utf-8")
        embed_lyrics_to_audio(str(mp3), str(lrc))

        lrc.write_text("[00:01.00]CHANGED\n", encoding="utf-8")
        embed_lyrics_to_audio(str(mp3), str(lrc), overwrite=False)
        tags = ID3(str(mp3))
        assert "CHANGED" not in tags.getall("USLT")[0].text

    def test_missing_files_return_false(self, tmp_path):
        from mmpd.id3_embed import embed_lyrics_to_audio
        assert embed_lyrics_to_audio(str(tmp_path / "nope.mp3"), str(tmp_path / "nope.lrc")) is False


# ============================================================================
# 8. Translate-only retrofit (mode suntik terjemahan)
# ============================================================================

class TestTranslateOnlyMode:
    def test_translate_only_preserves_original_lines(self, tmp_path, monkeypatch):
        """Mode translate-only TIDAK boleh menghapus baris asli — hanya menambah."""
        from mmpd.lyrics import process_translation
        from unittest.mock import patch, MagicMock

        lrc = tmp_path / "jiangnan.lrc"
        lrc.write_text("[00:01.00]風到這裡就是黏\n[00:05.00]雨到了這裡纏成線\n", encoding="utf-8")

        # Mock GoogleTranslator
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = lambda txt: "terjemahan baris" if txt and "1." not in txt else txt
        mock_module = MagicMock()
        mock_module.GoogleTranslator = MagicMock(return_value=mock_translator)
        mock_module.MyMemoryTranslator = MagicMock(side_effect=ImportError("no"))

        with patch.dict("sys.modules", {"deep_translator": mock_module}):
            process_translation(str(lrc), True)

        content = lrc.read_text(encoding="utf-8")
        assert "風到這裡就是黏" in content, "Aksara asli harus dipertahankan"
        assert "[00:01.00]" in content

    def test_run_translate_only_function_exists(self):
        from mmpd.modes.retrofit import run_translate_only
        assert callable(run_translate_only)

    def test_run_translate_only_no_lrc(self, tmp_path):
        from mmpd.modes.retrofit import run_translate_only
        assert run_translate_only(str(tmp_path), embed_id3=False) == 0

    def test_run_translate_only_processes_files(self, tmp_path, monkeypatch):
        """run_translate_only memproses file .lrc tanpa fetch internet."""
        from mmpd.modes import retrofit
        from unittest.mock import patch

        (tmp_path / "a.lrc").write_text("[00:01.00]Hello\n[00:02.00]World\n", encoding="utf-8")
        (tmp_path / "b.id.lrc").write_text("[00:01.00]skip\n", encoding="utf-8")
        (tmp_path / "c.lrc.bak").write_text("[00:01.00]skip\n", encoding="utf-8")

        # Mock peek (butuh network) → return None
        with patch.object(retrofit, "_peek_original_source_lines", return_value=None), \
             patch.object(retrofit, "process_translation") as mock_pt, \
             patch.object(retrofit, "_embed_lyrics_nearby", return_value=False):
            n = retrofit.run_translate_only(str(tmp_path), embed_id3=False)

        assert n == 1, "Hanya a.lrc yang harus diproses (bukan .id.lrc / .bak)"
        assert mock_pt.call_count == 1


# ============================================================================
# 9. Circuit breaker provider — perilaku benar
# ============================================================================

class TestProviderBreaker:
    def test_breaker_trips_on_exceptions(self):
        from mmpd import lyrics_providers as lp

        lp.reset_provider_breakers()
        for _ in range(3):
            lp.record_provider_fail("NetEase")
        assert lp.provider_is_tripped("NetEase")
        assert not lp.provider_is_tripped("Musixmatch")

        lp.record_provider_success("NetEase")
        assert not lp.provider_is_tripped("NetEase"), "Sukses harus reset breaker"
        lp.reset_provider_breakers()

    def test_search_with_timeout_guard(self):
        """call_with_timeout memanggil fn dan mengembalikan hasilnya."""
        from mmpd.lyrics_providers import call_with_timeout
        assert call_with_timeout(lambda a, b=None: f"{a}-{b}", "x", b="y", timeout=5) == "x-y"

    def test_search_timeout_raises(self):
        import time
        from mmpd.lyrics_providers import call_with_timeout
        with pytest.raises(TimeoutError):
            call_with_timeout(lambda: time.sleep(3), timeout=0.2)
