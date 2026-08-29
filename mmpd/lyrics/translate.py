"""
Translation — terjemahan lirik ke Bahasa Indonesia (bilingual LRC).

Strategi (dipertahankan dari versi lama, kini di modul sendiri — Fase A):
    1. Batch bernomor lewat Google Translate (konteks antar-baris)
    2. Baris gagal di-batch → retry paralel via run_concurrent
    3. Satu baris gagal TIDAK menggagalkan seluruh lagu
    4. Terjemahan SELALU dari aksara ASLI (source_lines snapshot)
"""

from __future__ import annotations

import os
import re

from mmpd.logger import get_logger
from mmpd.lyrics.lrc_format import (
    _looks_like_failed_translation,
    _strip_lrc_text,
    _write_bilingual_lrc,
    is_already_bilingual,
)
from mmpd.lyrics.transliterate import detect_script

_log = get_logger()

# Mapping kode bahasa langdetect → format MyMemory (BCP 47)
_LANG_MAP_MMYMEMORY = {
    "ja": "ja-JP",
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",
    "ko": "ko-KR",
    "th": "th-TH",
    "en": "en-US",
}


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
        with open(lrc_path, encoding="utf-8") as f:
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


# ============================================================================
# Internals: batch Google → fallback per-baris
# ============================================================================

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


def _extract_worker_text(results, index: int) -> str:
    """P0-fix: ambil teks hasil worker dari List[ConcurrentResult] dengan aman.

    Versi lama menulis `"text" in res[i]` pada objek ConcurrentResult
    (bukan dict) → TypeError yang ditelan except besar → fallback
    translate per-baris tidak pernah mengisi hasil.
    """
    try:
        item = results[index]
    except (IndexError, TypeError):
        return " "
    if item is None:
        return " "
    # ConcurrentResult punya .extra dict; worker translate menyimpan {"text": ...}
    extra = getattr(item, "extra", None)
    if isinstance(extra, dict) and extra.get("text"):
        return extra["text"]
    # Backward-compat: worker lama yang return dict langsung
    if isinstance(item, dict) and item.get("text"):
        return item["text"]
    return " "


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
                                translated_texts[global_i] = _extract_worker_text(res, local_m)
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
                translated_texts[global_i] = _extract_worker_text(res, local)

        i += BATCH
        if i < len(pending):
            import time
            time.sleep(0.5)  # D3: jeda 0.5 detik antar batch

    filled = sum(1 for t in translated_texts if t and t.strip())
    _log.info("Translation API: %d/%d baris berhasil (src=%s)", filled, len(pending), source_lang)
    return translated_texts
