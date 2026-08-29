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


_HIRAGANA_KATAKANA = re.compile(r'[぀-ヿ]')
_HAN = re.compile(r'[一-鿿]')
_HANGUL = re.compile(r'[가-힣]')
_THAI = re.compile(r'[฀-๿]')

def detect_script(text: str) -> str:
    if _HIRAGANA_KATAKANA.search(text): return "ja"
    if _HANGUL.search(text): return "ko"
    if _HAN.search(text): return "zh"
    if _THAI.search(text): return "th"
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
        # Logic baru: proses baris yang punya teks non-timestamp.
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
    from pypinyin import pinyin, Style

    new_lines = []
    for line in lines:
        # Fix Fase 3: proses baris yang punya teks non-timestamp
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
        # Fix Fase 3: proses baris yang punya teks non-timestamp
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
        # Fix Fase 3: proses baris yang punya teks non-timestamp
        text = re.sub(r"\[.*?\]", "", line).strip()
        if text:
            time_tags = "".join(re.findall(r"\[.*?\]", line))
            new_text = anyascii(text)
            new_lines.append(f"{time_tags}{new_text}\n")
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
    if transliterate_mode.startswith("❌"):
        return

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Gabungkan teks tanpa tag waktu untuk deteksi bahasa
        pure_text = " ".join([re.sub(r"\[.*?\]", "", line).strip() for line in lines if line.strip()])
        if not pure_text:
            return

        # Init engines lazily
        engines = {}

        def _get_kakasi():
            if "ja" not in engines:
                from pykakasi import kakasi
                engines["ja"] = kakasi()
            return engines["ja"]

        def _get_pinyin():
            if "zh" not in engines:
                from pypinyin import pinyin, Style
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
            if not text: return line
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


def _strip_lrc_text(line: str) -> str:
    """Ambil teks lirik tanpa tag waktu / meta."""
    return re.sub(r"\[.*?\]", "", line).strip()


def _detect_source_lang(texts) -> str:
    """Tebak kode bahasa source untuk mesin terjemahan."""
    blob = " ".join(t for t in texts if t and t.strip())
    script = detect_script(blob)
    return {
        "ja": "ja",
        "zh": "zh-CN",
        "ko": "ko",
        "th": "th",
    }.get(script, "auto")


def is_already_bilingual(lines) -> bool:
    """Deteksi LRC yang sudah bilingual (gabung ' / ' atau pasangan micro-offset)."""
    payload = 0
    slash_hits = 0
    parsed = []
    for line in lines:
        text = _strip_lrc_text(line)
        if not text:
            continue
        payload += 1
        if "  /  " in line or " / " in line:
            slash_hits += 1
        m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\]", line)
        if m:
            ts = int(m.group(1)) * 60 + float(m.group(2))
            parsed.append((ts, text.lower()))

    if payload and slash_hits / payload >= 0.35:
        return True

    close_pairs = 0
    for i in range(len(parsed) - 1):
        gap = parsed[i + 1][0] - parsed[i][0]
        if 0 < gap <= 0.85 and parsed[i][1] != parsed[i + 1][1]:
            close_pairs += 1
    return close_pairs >= max(3, len(parsed) // 5) if parsed else False


def process_translation(
    lrc_path: str,
    translate_mode: bool,
    source_lines=None,
) -> None:
    """
    Translate lirik ke Bahasa Indonesia, tambahkan sebagai baris bilingual.

    Penting untuk akurasi:
        Terjemahkan dari `source_lines` (lirik aksara asli) jika tersedia,
        lalu tempel hasilnya ke file tampilan (yang mungkin sudah di-latin-kan).
        Menerjemahkan pinyin/romaji jauh lebih tidak akurat daripada
        menerjemahkan Hanzi/Kana/Hangul asli.

    Args:
        lrc_path:       Path file .lrc (versi tampilan)
        translate_mode: True untuk aktifkan translation
        source_lines:   Opsional, baris LRC sumber (aksara asli) untuk diterjemahkan
    """
    if not os.path.exists(lrc_path) or not translate_mode:
        return

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        if is_already_bilingual(lines):
            _log.info("Translation skip (sudah bilingual): %s", os.path.basename(lrc_path))
            return

        display_texts = []
        source_texts = []
        for i, line in enumerate(lines):
            display = _strip_lrc_text(line)
            display_texts.append(display if display else " ")
            if source_lines is not None and i < len(source_lines):
                src = _strip_lrc_text(source_lines[i])
                source_texts.append(src if src else (display if display else " "))
            else:
                source_texts.append(display if display else " ")

        source_lang = _detect_source_lang(source_texts)

        try:
            from mmpd.cache import get_translation_cache, set_translation_cache
            cache_available = True
        except ImportError:
            cache_available = False
            _log.debug("mmpd.cache tidak tersedia, skip translation cache")

        cached_translations = [None] * len(source_texts)
        if cache_available:
            for i, text in enumerate(source_texts):
                if text.strip():
                    cached = get_translation_cache(text, source_lang, "id")
                    if cached is None and source_lang != "auto":
                        cached = get_translation_cache(text, "auto", "id")
                    if cached is not None:
                        cached_translations[i] = cached

            cache_hit_count = sum(1 for c in cached_translations if c is not None)
            non_empty_count = sum(1 for t in source_texts if t.strip())

            if cache_hit_count == non_empty_count and non_empty_count > 0:
                _log.info(
                    "Translation: 100%% cache hit (%d baris) untuk %s",
                    cache_hit_count,
                    os.path.basename(lrc_path),
                )
                translated_texts = [
                    cached_translations[i] if cached_translations[i] is not None else " "
                    for i in range(len(source_texts))
                ]
                _write_bilingual_lrc(lrc_path, lines, display_texts, translated_texts)
                return

            if cache_hit_count > 0:
                _log.info(
                    "Translation: %d/%d baris cache hit, translate sisanya via API",
                    cache_hit_count,
                    non_empty_count,
                )

        texts_to_translate_api = []
        indices_to_translate = []
        for i, text in enumerate(source_texts):
            if not cache_available or (cached_translations[i] is None and text.strip()):
                texts_to_translate_api.append(text)
                indices_to_translate.append(i)

        if not texts_to_translate_api:
            translated_texts = [
                cached_translations[i] if cached_translations[i] is not None else " "
                for i in range(len(source_texts))
            ]
            _write_bilingual_lrc(lrc_path, lines, display_texts, translated_texts)
            return

        api_translations = _translate_via_api(texts_to_translate_api, source_lang=source_lang)

        translated_texts = [" "] * len(source_texts)
        for i, idx in enumerate(indices_to_translate):
            if i < len(api_translations):
                translated_texts[idx] = api_translations[i]
                if cache_available and api_translations[i].strip():
                    set_translation_cache(
                        source_texts[idx], source_lang, "id",
                        api_translations[i], provider="google",
                    )
        for i in range(len(source_texts)):
            if cached_translations[i] is not None:
                translated_texts[i] = cached_translations[i]

        _write_bilingual_lrc(lrc_path, lines, display_texts, translated_texts)

    except Exception as e:
        _log.warning("Gagal menerjemahkan lirik %s: %s", os.path.basename(lrc_path), e)


def _looks_like_failed_translation(src: str, dest: str) -> bool:
    """True jika hasil terjemahan kosong, identik, atau masih aksara sumber."""
    if not dest or not dest.strip():
        return True
    s = src.strip().lower()
    d = dest.strip().lower()
    if s == d:
        return True
    if "error 500" in d or "mymemory warning" in d:
        return True
    src_script = detect_script(src)
    dest_script = detect_script(dest)
    if src_script != "latin" and dest_script == src_script:
        return True
    return False


def _parse_numbered_batch(translated: str, count: int):
    """Parse hasil batch bernomor '1. ...' kembali ke list."""
    lines = [ln.strip() for ln in translated.splitlines() if ln.strip()]
    result = [None] * count
    for ln in lines:
        m = re.match(r"^(\d+)[.)]\s*(.*)$", ln)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < count:
                result[idx] = m.group(2).strip()
    if sum(1 for x in result if x) >= max(1, count // 2):
        return result
    # fallback: jumlah baris sama
    if len(lines) == count:
        cleaned = [re.sub(r"^\d+[.)]\s*", "", ln).strip() for ln in lines]
        return cleaned
    return None


def _translate_batch_google(texts, source_lang: str):
    from deep_translator import GoogleTranslator

    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
    translator = GoogleTranslator(source=source_lang or "auto", target="id")
    raw = translator.translate(numbered)
    if not raw or "Error 500" in raw:
        raise RuntimeError("Google batch empty")
    parsed = _parse_numbered_batch(raw, len(texts))
    if not parsed:
        raise RuntimeError("Google batch parse failed")
    return parsed


def _translate_one_with_fallback(text: str, source_lang: str) -> str:
    """Translate satu baris: Google → MyMemory. Isolasi error per baris."""
    if not text.strip():
        return " "

    last_err = None
    for src in (source_lang, "auto"):
        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source=src or "auto", target="id").translate(text)
            if res and not _looks_like_failed_translation(text, res):
                return res.strip()
        except Exception as e:
            last_err = e

    mm_source = {
        "ja": "ja-JP",
        "zh-CN": "zh-CN",
        "zh": "zh-CN",
        "ko": "ko-KR",
        "th": "th-TH",
        "auto": "en-GB",
    }.get(source_lang or "auto", "en-GB")
    try:
        from deep_translator import MyMemoryTranslator
        res = MyMemoryTranslator(source=mm_source, target="id-ID").translate(text)
        if res and "MYMEMORY WARNING" not in res and not _looks_like_failed_translation(text, res):
            return res.strip()
    except Exception as e:
        last_err = e
        try:
            from deep_translator import MyMemoryTranslator
            res = MyMemoryTranslator(source="autodetect", target="id-ID").translate(text)
            if res and "MYMEMORY WARNING" not in res and res.strip():
                return res.strip()
        except Exception as e2:
            last_err = e2

    _log.debug("Translate line gagal (%s): %s", last_err, text[:40])
    return " "


def _worker_translate(text: str, source_lang: str) -> tuple[bool, str | None, dict]:
    try:
        res = _translate_one_with_fallback(text, source_lang)
        return True, None, {"text": res}
    except Exception as e:
        return False, str(e), {}

def _translate_via_api(texts_to_translate, source_lang: str = "auto"):
    """
    Translate list of texts ke Indonesia.
    Strategi:
        1. Batch bernomor lewat Google (konteks antar-baris → lebih akurat)
        2. Baris yang gagal di-batch di-retry paralel dengan run_concurrent
        3. Satu baris gagal TIDAK menggagalkan seluruh lagu
    """
    n = len(texts_to_translate)
    translated_texts = [" "] * n
    
    pending = []
    for i, text in enumerate(texts_to_translate):
        if text and text.strip():
            pending.append(i)
        else:
            translated_texts[i] = " "
            
    BATCH = 10
    i = 0
    from mmpd.concurrent import run_concurrent
    
    while i < len(pending):
        chunk_idx = pending[i:i + BATCH]
        chunk_txt = [texts_to_translate[j] for j in chunk_idx]
        used_batch = False
        if len(chunk_txt) >= 3:
            import time
            for attempt in range(3):
                try:
                    parsed = _translate_batch_google(chunk_txt, source_lang)
                    ok = 0
                    for local, global_i in enumerate(chunk_idx):
                        val = parsed[local] if parsed and local < len(parsed) and parsed[local] else None
                        if val and not _looks_like_failed_translation(chunk_txt[local], val):
                            translated_texts[global_i] = val
                            ok += 1
                    if ok >= max(1, len(chunk_txt) // 2):
                        used_batch = True
                        # Sisa yang kosong dikumpulkan
                        missing_idx = []
                        missing_txt = []
                        for local, global_i in enumerate(chunk_idx):
                            if translated_texts[global_i].strip() in ("",):
                                missing_idx.append(global_i)
                                missing_txt.append(chunk_txt[local])
                        if missing_txt:
                            res = run_concurrent(
                                missing_txt,
                                lambda t: _worker_translate(t, source_lang),
                                max_workers=5,
                                description="Retry translate"
                            )
                            for local_m, global_i in enumerate(missing_idx):
                                if res[local_m] and "text" in res[local_m]:
                                    translated_texts[global_i] = res[local_m]["text"]
                    break  # Success, exit retry loop
                except Exception as e:
                    _log.debug("Google batch attempt %d gagal (%s)", attempt + 1, e)
                    time.sleep(2)  # D3: backoff
            
        if not used_batch:
            res = run_concurrent(
                chunk_txt,
                lambda t: _worker_translate(t, source_lang),
                max_workers=5,
                description="Fallback translate"
            )
            for local, global_i in enumerate(chunk_idx):
                if res[local] and "text" in res[local]:
                    translated_texts[global_i] = res[local]["text"]
                    
        i += BATCH
        if i < len(pending):
            import time
            time.sleep(0.5)  # D3: jeda 0.5 detik antar batch
            
    filled = sum(1 for t in translated_texts if t and t.strip())
    _log.info("Translation API: %d/%d baris berhasil (src=%s)", filled, len(pending), source_lang)
    return translated_texts


def _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts):
    """
    Tulis file LRC bilingual dengan format standar industri atau gabungan.
    Konfigurasi format via ENV `MMPD_BILINGUAL_FORMAT` (gabung, pisah, id_only).
    """
    format_mode = os.environ.get("MMPD_BILINGUAL_FORMAT", "gabung")

    if len(translated_texts) < len(lines):
        translated_texts.extend([""] * (len(lines) - len(translated_texts)))

    def _parse_ts(ts_str):
        m = re.match(r"\[(\d+):(\d+\.\d+)\]", ts_str)
        if not m:
            m = re.match(r"\[(\d+):(\d+)\]", ts_str)
            if not m:
                return None
            return int(m.group(1)) * 60 + float(m.group(2))
        return int(m.group(1)) * 60 + float(m.group(2))

    def _format_ts(seconds):
        if seconds < 0:
            seconds = 0.0
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"[{mins:02d}:{secs:05.2f}]"

    parsed_lines = []
    for line in lines:
        match = re.match(r"(\[\d+:\d+(?:\.\d+)?\])", line)
        ts_val = _parse_ts(match.group(1)) if match else None
        parsed_lines.append((line, match.group(1) if match else None, ts_val))

    output = []
    output_id = []
    written = 0

    for i, (line, ts_str, ts_val) in enumerate(parsed_lines):
        t_text = translated_texts[i].strip() if translated_texts[i] else ""
        original_payload = texts_to_translate[i].strip() if i < len(texts_to_translate) else _strip_lrc_text(line)

        useful = (
            bool(t_text)
            and t_text.lower() != original_payload.lower()
            and not _looks_like_failed_translation(original_payload, t_text)
        )

        if useful and ts_str and ts_val is not None:
            original_text = line[len(ts_str):].rstrip("\n")
            written += 1
            if format_mode == "pisah":
                next_ts = None
                for j in range(i + 1, len(parsed_lines)):
                    if parsed_lines[j][2] is not None:
                        next_ts = parsed_lines[j][2]
                        break
                DEFAULT_OFFSET = 0.6
                if next_ts is None:
                    new_ts_val = ts_val + DEFAULT_OFFSET
                else:
                    gap = next_ts - ts_val
                    new_ts_val = ts_val + min(DEFAULT_OFFSET, max(0.25, gap * 0.4))
                new_ts_str = _format_ts(new_ts_val)
                output.append(line.rstrip("\n"))
                output.append(f"{new_ts_str}{t_text}")
            elif format_mode == "id_only":
                output.append(line.rstrip("\n"))
                output_id.append(f"{ts_str}{t_text}")
            else:
                combined_line = f"{ts_str}{original_text}  /  {t_text}"
                output.append(combined_line)
        else:
            output.append(line.rstrip("\n"))
            if format_mode == "id_only" and ts_str:
                output_id.append(line.rstrip("\n"))

    if format_mode == "id_only":
        id_path = lrc_path.replace(".lrc", ".id.lrc")
        atomic_write_text(id_path, "\n".join(output_id) + "\n")

    atomic_write_text(lrc_path, "\n".join(output) + "\n")
    _log.info(
        "Translation OK: %s (mode=%s, lines=%d)",
        os.path.basename(lrc_path),
        format_mode,
        written,
    )


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
            from mmpd.utils.matching import clean_search_query
            clean_title = clean_search_query(title)

        # === Strategi 1: LyricsChain (LRCLIB → syncedlyrics) ===
        lrc_text: Optional[str] = None
        try:
            from mmpd.lyrics_providers import build_default_chain
            from mmpd.types import TrackInfo

            track = TrackInfo(title=clean_title)
            chain = build_default_chain(clean_title)
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
                        result2 = build_default_chain(clean_title).search(track_info)
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
            original_lines = [
                (ln if ln.endswith("\n") else ln + "\n")
                for ln in lrc_text.splitlines()
            ]
            atomic_write_text(lrc_path, lrc_text)
            # Transliterasi MAY overwrite aksara asli. Terjemahan HARUS
            # memakai snapshot asli agar Mandarin/Jepang/Korea tidak
            # diterjemahkan dari pinyin/romaji (akurasi anjlok).
            process_transliteration(lrc_path, transliterate_mode)
            process_translation(lrc_path, translate_mode, source_lines=original_lines)
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
