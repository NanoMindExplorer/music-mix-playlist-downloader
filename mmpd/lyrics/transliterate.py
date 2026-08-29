"""
Transliterasi — aksara asing (JA/ZH/KO/TH/YUE) → alfabet Latin.

Modul ini berisi:
- detect_script: deteksi kasar jenis aksara dari teks
- process_transliteration: pipeline transliterasi file LRC in-place,
  dengan RETURN snapshot baris asli (kontrak Fase L)
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from mmpd.logger import get_logger
from mmpd.utils.fs import atomic_write_text

_log = get_logger()

# Mapping kode bahasa langdetect → library transliterasi yang dipakai
_LANGUAGE_TRANSLITERATORS = {
    "ja": "pykakasi",
    "zh-cn": "pypinyin",
    "zh-tw": "pypinyin",
    "ko": "korean_romanizer",
}

# Bahasa yang sudah pakai alfabet Latin — skip transliterasi
_LATIN_LANGUAGES = {"en", "id", "es", "fr", "de", "it", "nl", "tl", "pt", "ro"}

_HIRAGANA_KATAKANA = re.compile(r"[぀-ヿ]")
_HAN = re.compile(r"[一-鿿]")
_HANGUL = re.compile(r"[가-힣]")
_THAI = re.compile(r"[ก-๛]")  # U+0E01..U+0E5F (Thai block) — escape eksplisit anti-corrupt


def detect_script(text: str) -> str:
    """Deteksi jenis aksara: ja / ko / zh / th / latin."""
    if _HIRAGANA_KATAKANA.search(text):
        return "ja"
    if _HANGUL.search(text):
        return "ko"
    if _HAN.search(text):
        return "zh"
    if _THAI.search(text):
        return "th"
    return "latin"


def _transliterate_japanese(lines: List[str]) -> List[str]:
    """Transliterasi aksara Jepang (Kanji/Hiragana/Katakana) → Romaji (Hepburn)."""
    from pykakasi import kakasi

    k = kakasi()
    new_lines = []
    for line in lines:
        # Fix Fase 3: bug lama `not line.strip().startswith("[")` akan skip baris
        # yang dimulai dengan timestamp [00:00.00] — padahal baris itu justru
        # yang perlu di-transliterasi (teks lirik ada setelah timestamp).
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tags = "".join(re.findall(r"\[.*?\]", line))
            conv = k.convert(text)
            new_text = "".join([item["hepburn"] for item in conv])
            new_lines.append(f"{time_tags}{new_text}\n")
        else:
            new_lines.append(line)
    return new_lines


def _transliterate_chinese(lines: List[str]) -> List[str]:
    """Transliterasi Hanzi (Simplified/Traditional) → Pinyin."""
    from pypinyin import Style, pinyin

    new_lines = []
    for line in lines:
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tags = "".join(re.findall(r"\[.*?\]", line))
            py_list = pinyin(text, style=Style.NORMAL)
            # Fix B3 (Fase 1): gunakan spasi sebagai pemisah suku kata
            new_text = " ".join([item[0] for item in py_list])
            new_lines.append(f"{time_tags}{new_text}\n")
        else:
            new_lines.append(line)
    return new_lines


def _transliterate_korean(lines: List[str]) -> List[str]:
    """Transliterasi Hangul → Latin (Revised Romanization)."""
    from korean_romanizer.romanizer import Romanizer

    new_lines = []
    for line in lines:
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tags = "".join(re.findall(r"\[.*?\]", line))
            try:
                new_text = Romanizer(text).romanize()
                new_lines.append(f"{time_tags}{new_text}\n")
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
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tags = "".join(re.findall(r"\[.*?\]", line))
            new_text = anyascii(text)
            new_lines.append(f"{time_tags}{new_text}\n")
        else:
            new_lines.append(line)
    return new_lines


def process_transliteration(lrc_path: str, transliterate_mode: str) -> Optional[List[str]]:
    """
    Ubah huruf asing (Jepang/Mandarin/Korea/dll) di file LRC menjadi
    Romaji/Pinyin/Latin tanpa merusak tag waktu [mm:ss.xx].

    Fase L: mengembalikan SNAPSHOT baris asli (aksara asli sebelum
    di-transliterasi) supaya pemanggil bisa meneruskannya ke
    process_translation(source_lines=...). Kontrak pipeline yang benar:

        original = process_transliteration(lrc, mode)   # file jadi latin
        process_translation(lrc, True, source_lines=original)  # terjemah dari ASLI

    Tanpa snapshot, terjemahan akan dikerjakan dari pinyin/romaji —
    akurasi anjlok drastis.

    Args:
        lrc_path:           Path file .lrc
        transliterate_mode:  Mode transliterasi:
            "❌ 1" — biarkan aslinya (skip)
            "🇯🇵 2" — Jepang → Romaji (pykakasi)
            "🇨🇳 3" — Mandarin → Pinyin (pypinyin)
            "🤖 4/5" — auto-detect bahasa (langdetect) + pilih transliterator

    Returns:
        List baris asli (sebelum transliterasi), atau None kalau file tidak
        ada / mode skip / terjadi error. Caller LAMA boleh mengabaikan return.
    """
    if not os.path.exists(lrc_path):
        return None
    if transliterate_mode.startswith("❌"):
        return None

    try:
        with open(lrc_path, encoding="utf-8") as f:
            lines = f.readlines()

        # Fase L: snapshot asli SEBELUM ada modifikasi — dikembalikan ke caller
        original_snapshot = list(lines)

        # Gabungkan teks tanpa tag waktu untuk deteksi bahasa
        pure_text = " ".join([re.sub(r"\[.*?\]", "", line).strip() for line in lines if line.strip()])
        if not pure_text:
            return None

        # Init engines lazily
        engines = {}

        def _get_kakasi():
            if "ja" not in engines:
                from pykakasi import kakasi
                engines["ja"] = kakasi()
            return engines["ja"]

        def _get_pinyin():
            if "zh" not in engines:
                from pypinyin import Style, pinyin
                engines["zh"] = (pinyin, Style)
            return engines["zh"]

        def _get_korean():
            if "ko" not in engines:
                from korean_romanizer.romanizer import Romanizer
                engines["ko"] = Romanizer
            return engines["ko"]

        def _get_anyascii():
            if "anyascii" not in engines:
                from anyascii import anyascii
                engines["anyascii"] = anyascii
            return engines["anyascii"]

        def _trans_line(line: str, lang: str) -> str:
            text = re.sub(r"\[.*?\]", "", line).strip()
            if not text:
                return line
            time_tags = "".join(re.findall(r"\[.*?\]", line))

            try:
                if lang == "ja":
                    k = _get_kakasi()
                    conv = k.convert(text)
                    new_text = "".join([item["hepburn"] for item in conv])
                    return f"{time_tags}{new_text}\n"
                elif lang in ("zh", "zh-cn", "zh-tw"):
                    pinyin, Style = _get_pinyin()
                    py_list = pinyin(text, style=Style.NORMAL)
                    new_text = " ".join([item[0] for item in py_list])
                    return f"{time_tags}{new_text}\n"
                elif lang == "ko":
                    Romanizer = _get_korean()
                    new_text = Romanizer(text).romanize()
                    return f"{time_tags}{new_text}\n"
                elif lang == "yue":
                    import ToJyutping
                    new_text = ToJyutping.get_jyutping_text(text)
                    return f"{time_tags}{new_text}\n"
                elif lang == "th":
                    from pythainlp.transliterate import romanize
                    new_text = romanize(text, engine="royin")
                    return f"{time_tags}{new_text}\n"
            except Exception as e:
                _log.warning("Transliterator error: %s", e)
            return line

        new_lines = []
        target_lang = "auto"
        if transliterate_mode.startswith("🤖"):
            for line in lines:
                text = re.sub(r"\[.*?\]", "", line).strip()
                if not text:
                    new_lines.append(line)
                    continue
                lang = detect_script(text)
                if lang == "latin":
                    new_lines.append(line)
                else:
                    new_lines.append(_trans_line(line, lang))
        else:
            if transliterate_mode.startswith("🇯🇵"):
                target_lang = "ja"
            elif transliterate_mode.startswith("🇨🇳"):
                target_lang = "zh"
            elif "Kanton" in transliterate_mode or transliterate_mode.startswith("🇭🇰"):
                target_lang = "yue"
            else:
                target_lang = "latin"

            for line in lines:
                new_lines.append(_trans_line(line, target_lang))

        # Tulis hasil secara atomik
        atomic_write_text(lrc_path, "".join(new_lines))
        _log.info("Transliteration OK: %s (lang=%s)", os.path.basename(lrc_path), target_lang)
        return original_snapshot

    except Exception as e:
        _log.warning("Gagal transliterasi %s: %s", os.path.basename(lrc_path), e)
        return None
