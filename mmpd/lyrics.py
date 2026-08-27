"""
Lyrics processing pipeline — transliteration, translation, Huawei sync.

Modul ini berisi 4 fungsi yang sebelumnya ada di downloader.py:
    1. sync_huawei_lrc        — copy .lrc ke folder Musiclrc Huawei
    2. process_transliteration — konversi aksara asing (Jepang/Mandarin/Korea/Arab/Thai)
    3. process_translation      — translate lirik ke Indonesia (bilingual LRC)
    4. fetch_synced_lyrics      — orchestrator: search lyrics via LyricsChain,
                                  apply transliteration + translation + sync

Dipisah ke modul terpisah agar:
- Mudah di-test (mock lyrics_providers untuk unit test)
- Tidak bloat downloader.py (Fase 2.2 goal: downloader.py jadi thin entry)
- Konsisten dengan arsitektur modular Fase 2.1
"""

from __future__ import annotations

import os
import re
import shutil
import time
from typing import List, Optional

from mmpd.config import get_musiclrc_dir, is_termux
from mmpd.logger import get_logger
from mmpd.utils.fs import atomic_write_text

_log = get_logger()


# ============================================================================
# 1. SYNC HUAWEI MUSICLRC
# ============================================================================

def sync_huawei_lrc(lrc_path: str) -> None:
    """
    Salin file .lrc ke folder khusus Musiclrc bawaan Huawei/Android.

    Kebutuhan: Huawei Music Player mensyaratkan lirik (.lrc) berada di
    folder `Internal/Music/Musiclrc`. Tanpa sync ini, lirik tidak muncul
    di karaoke mode Huawei.

    Args:
        lrc_path: Path file .lrc yang akan di-sync.

    Behavior:
        - Hanya jalan di Termux (skip di Linux/macOS/Windows)
        - Skip jika file source tidak ada
        - Buat folder target jika belum ada
        - Copy (bukan move) — file original tetap utuh
    """
    if not is_termux():
        return

    if not os.path.exists(lrc_path):
        _log.debug("sync_huawei_lrc skip (source tidak ada): %s", lrc_path)
        return

    huawei_dir = get_musiclrc_dir()
    try:
        os.makedirs(huawei_dir, exist_ok=True)
        filename = os.path.basename(lrc_path)
        target = os.path.join(huawei_dir, filename)
        shutil.copy2(lrc_path, target)
        _log.debug("LRC synced to Huawei Musiclrc: %s", filename)
    except Exception as e:
        _log.warning("sync_huawei_lrc failed for %s: %s", os.path.basename(lrc_path), e)


# ============================================================================
# 2. TRANSLITERATION (Romaji/Pinyin/Latin)
# ============================================================================

# Mapping kode bahasa langdetect → library transliterasi yang dipakai
_LANGUAGE_TRANSLITERATORS = {
    "ja": "pykakasi",
    "zh-cn": "pypinyin",
    "zh-tw": "pypinyin",
    "ko": "korean_romanizer",
}

# Bahasa yang sudah pakai alfabet Latin — skip transliterasi
_LATIN_LANGUAGES = {"en", "id", "es", "fr", "de", "it", "nl", "tl", "pt", "ro"}


def _transliterate_japanese(lines: List[str]) -> List[str]:
    """Transliterasi aksara Jepang (Kanji/Hiragana/Katakana) → Romaji (Hepburn)."""
    from pykakasi import kakasi

    k = kakasi()
    new_lines = []
    for line in lines:
        # Fix Fase 3: bug lama `not line.strip().startswith("[")` akan skip baris
        # yang dimulai dengan timestamp [00:00.00] — padahal baris itu justru
        # yang perlu di-transliterasi (teks lirik ada setelah timestamp).
        # Logic baru: proses baris yang punya teks non-timestamp.
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tag = re.match(r"\[.*?\]", line)
            conv = k.convert(text)
            new_text = "".join([item["hepburn"] for item in conv])
            new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
        else:
            new_lines.append(line)
    return new_lines


def _transliterate_chinese(lines: List[str]) -> List[str]:
    """Transliterasi Hanzi (Simplified/Traditional) → Pinyin."""
    from pypinyin import pinyin, Style

    new_lines = []
    for line in lines:
        # Fix Fase 3: proses baris yang punya teks non-timestamp
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tag = re.match(r"\[.*?\]", line)
            py_list = pinyin(text, style=Style.NORMAL)
            # Fix B3 (Fase 1): gunakan spasi sebagai pemisah suku kata
            new_text = " ".join([item[0] for item in py_list])
            new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
        else:
            new_lines.append(line)
    return new_lines


def _transliterate_korean(lines: List[str]) -> List[str]:
    """Transliterasi Hangul → Latin (Revised Romanization)."""
    from korean_romanizer.romanizer import Romanizer

    new_lines = []
    for line in lines:
        # Fix Fase 3: proses baris yang punya teks non-timestamp
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tag = re.match(r"\[.*?\]", line)
            try:
                new_text = Romanizer(text).romanize()
                new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
            except Exception as e:
                _log.warning("Romanizer gagal untuk baris (%s). Pakai teks asli.", e)
                new_lines.append(line)
        else:
            new_lines.append(line)
    return new_lines


def _transliterate_universal(lines: List[str]) -> List[str]:
    """Fallback universal untuk bahasa lain (Thai, Arab, Rusia, dll.) — pakai anyascii."""
    from anyascii import anyascii

    new_lines = []
    for line in lines:
        # Fix Fase 3: proses baris yang punya teks non-timestamp
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tag = re.match(r"\[.*?\]", line)
            new_text = anyascii(text)
            new_lines.append(f"{time_tag.group(0) if time_tag else ''}{new_text}\n")
        else:
            new_lines.append(line)
    return new_lines


def process_transliteration(lrc_path: str, transliterate_mode: str) -> None:
    """
    Ubah huruf asing (Jepang/Mandarin/Korea/dll) di file LRC menjadi
    Romaji/Pinyin/Latin tanpa merusak tag waktu [mm:ss.xx].

    Args:
        lrc_path:           Path file .lrc
        transliterate_mode:  Mode transliterasi:
            "❌ 1" — biarkan aslinya (skip)
            "🇯🇵 2" — Jepang → Romaji (pykakasi)
            "🇨🇳 3" — Mandarin → Pinyin (pypinyin)
            "🤖 4" — auto-detect bahasa (langdetect) + pilih transliterator

    Behavior:
        - Skip jika file tidak ada atau mode "❌ 1"
        - Skip jika teks ternyata sudah alfabet Latin (mode auto)
        - Tulis hasil via atomic_write_text (cegah korupsi saat crash)
    """
    if not os.path.exists(lrc_path):
        return
    if transliterate_mode.startswith("❌ 1"):
        return

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Gabungkan teks tanpa tag waktu untuk deteksi bahasa
        pure_text = " ".join([re.sub(r"\[.*?\]", "", line).strip() for line in lines if line.strip()])
        if not pure_text:
            return

        # Tentukan bahasa target
        target_lang = ""
        if transliterate_mode.startswith("🤖 4"):
            import langdetect
            try:
                target_lang = langdetect.detect(pure_text)
            except Exception:
                _log.warning("langdetect gagal, skip transliterasi")
                return

            if target_lang in _LATIN_LANGUAGES:
                _log.debug("Bahasa %s sudah Latin, skip transliterasi", target_lang)
                return
        elif transliterate_mode.startswith("🇯🇵 2"):
            target_lang = "ja"
        elif transliterate_mode.startswith("🇨🇳 3"):
            target_lang = "zh-cn"

        # Pilih transliterator sesuai bahasa
        if target_lang == "ja":
            new_lines = _transliterate_japanese(lines)
        elif target_lang in ("zh-cn", "zh-tw"):
            new_lines = _transliterate_chinese(lines)
        elif target_lang == "ko":
            new_lines = _transliterate_korean(lines)
        else:
            new_lines = _transliterate_universal(lines)

        # Tulis hasil secara atomik
        atomic_write_text(lrc_path, "".join(new_lines))
        _log.info("Transliteration OK: %s (lang=%s)", os.path.basename(lrc_path), target_lang)

    except Exception as e:
        _log.warning("Gagal transliterasi %s: %s", os.path.basename(lrc_path), e)


# ============================================================================
# 3. TRANSLATION (Bilingual LRC — Indonesia)
# ============================================================================

# Mapping kode bahasa langdetect → format MyMemory (BCP 47)
_LANG_MAP_MMYMEMORY = {
    "ja": "ja-JP",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",
    "ko": "ko-KR",
    "th": "th-TH",
    "en": "en-US",
}


def process_translation(lrc_path: str, translate_mode: bool) -> None:
    """
    Translate lirik ke Bahasa Indonesia, tambahkan sebagai baris bilingual
    dengan timestamp identik. Format LRC standar industri:
        [00:01.23] original text
        [00:01.23] terjemahan

    Args:
        lrc_path:       Path file .lrc
        translate_mode: True untuk aktifkan translation, False untuk skip

    Behavior:
        - Skip jika file tidak ada atau translate_mode False
        - Pakai Google Translate (deep_translator.GoogleTranslator)
        - Fallback ke MyMemory jika Google error 500 atau rate-limited
        - Tulis hasil via atomic_write_text (cegah korupsi)
    """
    if not os.path.exists(lrc_path) or not translate_mode:
        return

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        from deep_translator import GoogleTranslator, MyMemoryTranslator
        import langdetect

        # Kumpulkan semua baris teks (tanpa timestamp) untuk translate batch
        texts_to_translate = []
        for line in lines:
            text = re.sub(r"\[.*?\]", "", line).strip()
            texts_to_translate.append(text if text else " ")

        translated_texts: List[str] = []

        # === Strategi 1: Google Translate (batch, cepat) ===
        try:
            translator = GoogleTranslator(source="auto", target="id")
            combined_text = "\n".join(texts_to_translate)
            res = translator.translate(combined_text)
            if not res or "Error 500" in res:
                raise Exception("Google Translate Web API Error 500")
            translated_texts = res.split("\n")
        except Exception as e:
            _log.warning("Google Translate gagal (%s). Beralih ke MyMemory...", e)

            # === Strategi 2: MyMemory (chunked, lebih lambat tapi reliable) ===
            pure_text = " ".join([t for t in texts_to_translate if t.strip()])
            if not pure_text:
                return

            try:
                lang = langdetect.detect(pure_text)
            except Exception:
                lang = "en"

            source_lang = _LANG_MAP_MMYMEMORY.get(lang, f"{lang}-{lang.upper()}")

            try:
                # MyMemory limit 500 karakter per request
                mm = MyMemoryTranslator(source=source_lang, target="id-ID")
                current_chunk: List[str] = []
                current_len = 0
                for text in texts_to_translate:
                    if current_len + len(text) + 1 > 450:
                        combined = "\n".join(current_chunk)
                        res = mm.translate(combined)
                        translated_texts.extend(res.split("\n"))
                        current_chunk = [text]
                        current_len = len(text)
                        time.sleep(1)  # Hindari rate limit MyMemory
                    else:
                        current_chunk.append(text)
                        current_len += len(text) + 1

                if current_chunk:
                    combined = "\n".join(current_chunk)
                    res = mm.translate(combined)
                    translated_texts.extend(res.split("\n"))
            except Exception as e2:
                _log.warning("Semua mesin terjemahan gagal: %s", e2)
                return

        # Pastikan jumlah array cocok (MyMemory kadang potong baris kosong)
        if len(translated_texts) < len(lines):
            translated_texts.extend([""] * (len(lines) - len(translated_texts)))

        # Build output bilingual — dua baris dengan timestamp identik
        output: List[str] = []
        for i, line in enumerate(lines):
            output.append(line.rstrip("\n"))
            t_text = translated_texts[i].strip() if translated_texts[i] else ""
            if t_text and t_text.lower() != texts_to_translate[i].strip().lower():
                match = re.match(r"(\[.*?\])", line)
                if match:
                    timestamp = match.group(1)
                    # Fix B4 (Fase 1): pakai dua baris timestamp identik
                    # (standar LRC bilingual) — bukan format parenthetical
                    output.append(f"{timestamp}{t_text}")

        atomic_write_text(lrc_path, "\n".join(output))
        _log.info("Translation OK: %s", os.path.basename(lrc_path))

    except Exception as e:
        _log.warning("Gagal menerjemahkan lirik %s: %s", os.path.basename(lrc_path), e)


# ============================================================================
# 4. ORCHESTRATOR: fetch_synced_lyrics
# ============================================================================

def fetch_synced_lyrics(
    title: str,
    lrc_path: str,
    sync_huawei: bool,
    transliterate_mode: str = "❌ 1",
    override_query: Optional[str] = None,
    translate_mode: bool = False,
) -> bool:
    """
    Cari lirik sinkron, tulis ke lrc_path, lalu apply transliteration +
    translation + Huawei sync.

    Pipeline:
        1. Build search query (clean atau override)
        2. Cari via LyricsChain (LRCLIB → syncedlyrics, Fase 2.1)
        3. Jika gagal: coba iTunes "Formula Cerdas" untuk tebak judul resmi
        4. Tulis hasil via atomic_write_text
        5. process_transliteration (Romaji/Pinyin/Latin)
        6. process_translation (bilingual Indonesia)
        7. sync_huawei_lrc (copy ke Musiclrc folder)

    Args:
        title:              Judul lagu (mentah, mungkin ada bracket/promo)
        lrc_path:           Path output file .lrc
        sync_huawei:        True untuk sync ke folder Huawei Musiclrc
        transliterate_mode: Mode transliterasi (lihat process_transliteration)
        override_query:     Jika diisi, pakai ini sebagai search query
                            (untuk Mode 2 — input judul Spotify manual)
        translate_mode:     True untuk aktifkan translation bilingual

    Returns:
        True jika lirik ditemukan & ditulis, False jika tidak ditemukan.
    """
    _log.info("fetch_synced_lyrics: title='%s', override=%s", title, override_query)
    try:
        # Build search query
        if override_query:
            clean_title = override_query.strip()
        else:
            clean_title = re.sub(r"\[.*?\]|\(.*?\)|【.*?】", "", title).strip()

        # === Strategi 1: LyricsChain (LRCLIB → syncedlyrics) ===
        lrc_text: Optional[str] = None
        try:
            from mmpd.lyrics_providers import build_default_chain
            from mmpd.types import TrackInfo

            track = TrackInfo(title=clean_title)
            chain = build_default_chain()
            result = chain.search(track)
            if result and result.best_lyrics:
                lrc_text = result.best_lyrics
                _log.info("Lyrics found via %s for '%s'", result.provider, clean_title)
        except ImportError:
            # Fallback kalau mmpd package tidak terinstal — pakai syncedlyrics langsung
            try:
                import syncedlyrics
                lrc_text = syncedlyrics.search(clean_title)
            except Exception as e:
                _log.warning("syncedlyrics fallback gagal: %s", e)

        # === Strategi 2: iTunes "Formula Cerdas" untuk tebak judul resmi ===
        if not lrc_text and not override_query:
            try:
                import requests
                from urllib.parse import quote
                smart_query = re.sub(
                    r"(?i)(official|music video|mv|lyric|video|audio|cover)",
                    "",
                    clean_title,
                ).strip()
                encoded_query = quote(smart_query)
                res = requests.get(
                    f"https://itunes.apple.com/search?term={encoded_query}&entity=song&limit=1",
                    timeout=5,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                res.raise_for_status()
                data = res.json()
                if data.get("resultCount", 0) > 0:
                    track_name = data["results"][0]["trackName"]
                    artist_name = data["results"][0]["artistName"]
                    smart_title = f"{artist_name} {track_name}"
                    _log.info("iTunes Formula Cerdas: '%s' → '%s'", clean_title, smart_title)

                    # Coba lagi dengan smart_title via LyricsChain
                    try:
                        from mmpd.lyrics_providers import build_default_chain
                        from mmpd.types import TrackInfo
                        track_info = TrackInfo(title=track_name, artist=artist_name)
                        result2 = build_default_chain().search(track_info)
                        if result2 and result2.best_lyrics:
                            lrc_text = result2.best_lyrics
                    except ImportError:
                        import syncedlyrics
                        lrc_text = syncedlyrics.search(smart_title)
            except ImportError:
                _log.warning("requests tidak terinstal, iTunes fallback dilewati")
            except Exception as e:
                _log.warning("iTunes Formula Cerdas gagal: %s", e)

        # === Tulis hasil & jalankan post-processing ===
        if lrc_text:
            atomic_write_text(lrc_path, lrc_text)
            process_transliteration(lrc_path, transliterate_mode)
            process_translation(lrc_path, translate_mode)
            if sync_huawei:
                sync_huawei_lrc(lrc_path)
            _log.info("Lyrics written to %s", lrc_path)
            return True
        else:
            _log.warning("No lyrics found for: %s", clean_title)
            return False

    except Exception as e:
        _log.error("fetch_synced_lyrics failed for '%s': %s", title, e, exc_info=True)
        return False
