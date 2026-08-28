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


def process_translation(lrc_path: str, translate_mode: bool) -> None:
    """
    Translate lirik ke Bahasa Indonesia, tambahkan sebagai baris bilingual
    dengan timestamp identik. Format LRC standar industri:
        [00:01.23] original text
        [00:01.23] terjemahan

    Fase 4: cek translation cache (SQLite) sebelum hit API.
    Cache key: SHA256(source_text + source_lang + target_lang).

    Args:
        lrc_path:       Path file .lrc
        translate_mode: True untuk aktifkan translation, False untuk skip

    Behavior:
        - Skip jika file tidak ada atau translate_mode False
        - Fase 4: cek translation cache dulu (SQLite) - kalau 100% hit, skip API
        - Pakai Google Translate (deep_translator.GoogleTranslator)
        - Fallback ke MyMemory jika Google error 500 atau rate-limited
        - Tulis hasil via atomic_write_text (cegah korupsi)
    """
    if not os.path.exists(lrc_path) or not translate_mode:
        return

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Kumpulkan semua baris teks (tanpa timestamp) untuk translate batch
        texts_to_translate = []
        for line in lines:
            text = re.sub(r"\[.*?\]", "", line).strip()
            texts_to_translate.append(text if text else " ")

        # === Fase 4: Cek translation cache per-baris ===
        try:
            from mmpd.cache import get_translation_cache, set_translation_cache
            cache_available = True
        except ImportError:
            cache_available = False
            _log.debug("mmpd.cache tidak tersedia, skip translation cache")

        cached_translations = [None] * len(texts_to_translate)
        if cache_available:
            for i, text in enumerate(texts_to_translate):
                if text.strip():
                    cached = get_translation_cache(text, "auto", "id")
                    if cached is not None:
                        cached_translations[i] = cached

            # Cek apakah SEMUA baris ada di cache
            cache_hit_count = sum(1 for c in cached_translations if c is not None)
            non_empty_count = sum(1 for t in texts_to_translate if t.strip())

            if cache_hit_count == non_empty_count and non_empty_count > 0:
                _log.info("Translation: 100% cache hit (%d baris) untuk %s",
                          cache_hit_count, os.path.basename(lrc_path))
                translated_texts = [
                    cached_translations[i] if cached_translations[i] is not None else " "
                    for i in range(len(texts_to_translate))
                ]
                _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts)
                return

            if cache_hit_count > 0:
                _log.info(
                    "Translation: %d/%d baris cache hit, translate sisanya via API",
                    cache_hit_count,
                    non_empty_count,
                )

        # Translate hanya baris yang miss cache (atau semua kalau no cache)
        texts_to_translate_api = []
        indices_to_translate = []
        for i, text in enumerate(texts_to_translate):
            if not cache_available or (cached_translations[i] is None and text.strip()):
                texts_to_translate_api.append(text)
                indices_to_translate.append(i)

        if not texts_to_translate_api:
            # Semua cached
            translated_texts = [
                cached_translations[i] if cached_translations[i] is not None else " "
                for i in range(len(texts_to_translate))
            ]
            _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts)
            return

        # Translate via API (Google -> MyMemory fallback)
        api_translations = _translate_via_api(texts_to_translate_api)

        # Merge: cached + api results
        translated_texts = [" "] * len(texts_to_translate)
        for i, idx in enumerate(indices_to_translate):
            if i < len(api_translations):
                translated_texts[idx] = api_translations[i]
                # Fase 4: cache hasil API
                if cache_available:
                    set_translation_cache(
                        texts_to_translate[idx], "auto", "id",
                        api_translations[i], provider="google",
                    )
        # Isi yang cached
        for i in range(len(texts_to_translate)):
            if cached_translations[i] is not None:
                translated_texts[i] = cached_translations[i]

        _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts)

    except Exception as e:
        _log.warning("Gagal menerjemahkan lirik %s: %s", os.path.basename(lrc_path), e)


def _translate_via_api(texts_to_translate):
    """
    Translate list of texts via Google Translate (fallback MyMemory).
    Menggunakan translasi per-baris secara konruen untuk menjamin alignment 1:1.
    """
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    import concurrent.futures

    translated_texts = [""] * len(texts_to_translate)
    
    # === Strategi 1: Google Translate (concurrency per baris) ===
    try:
        translator = GoogleTranslator(source="auto", target="id")
        
        def _trans_google(idx, text):
            if not text.strip(): return idx, " "
            res = translator.translate(text)
            if not res or "Error 500" in res:
                raise Exception("API Error")
            return idx, res

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_trans_google, i, t) for i, t in enumerate(texts_to_translate)]
            for f in concurrent.futures.as_completed(futures):
                idx, res = f.result()
                translated_texts[idx] = res
        return translated_texts
    except Exception as e:
        _log.warning("Google Translate gagal (%s). Beralih ke MyMemory...", e)

        # === Strategi 2: MyMemory (lebih lambat tapi reliable) ===
        try:
            translator_mm = MyMemoryTranslator(source="auto", target="id")
            def _trans_mm(idx, text):
                if not text.strip(): return idx, " "
                res = translator_mm.translate(text)
                if not res: return idx, " "
                if "MYMEMORY WARNING" in res:
                    raise Exception("MyMemory Rate Limit")
                return idx, res

            translated_texts_mm = [""] * len(texts_to_translate)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(_trans_mm, i, t) for i, t in enumerate(texts_to_translate)]
                for f in concurrent.futures.as_completed(futures):
                    idx, res = f.result()
                    translated_texts_mm[idx] = res
            return translated_texts_mm
        except Exception as e2:
            _log.warning("Semua mesin terjemahan gagal: %s", e2)
            return [" "] * len(texts_to_translate)


def _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts):
    """
    Tulis file LRC bilingual dengan format standar industri atau gabungan.
    Konfigurasi format via ENV `MMPD_BILINGUAL_FORMAT` (gabung, pisah, id_only).
    """
    import os
    format_mode = os.environ.get("MMPD_BILINGUAL_FORMAT", "gabung")

    if len(translated_texts) < len(lines):
        translated_texts.extend([""] * (len(lines) - len(translated_texts)))

    def _parse_ts(ts_str):
        # ts_str is like "[00:01.23]"
        m = re.match(r"\[(\d+):(\d+\.\d+)\]", ts_str)
        if not m: return None
        return int(m.group(1)) * 60 + float(m.group(2))

    def _format_ts(seconds):
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"[{mins:02d}:{secs:05.2f}]"

    # Pre-parse timestamps untuk micro-offset
    parsed_lines = []
    for line in lines:
        match = re.match(r"(\[\d+:\d+\.\d+\])", line)
        ts_val = _parse_ts(match.group(1)) if match else None
        parsed_lines.append((line, match.group(1) if match else None, ts_val))

    output = []
    output_id = []
    
    for i, (line, ts_str, ts_val) in enumerate(parsed_lines):
        t_text = translated_texts[i].strip() if translated_texts[i] else ""
        
        if t_text and t_text.lower() != texts_to_translate[i].strip().lower() and ts_str and ts_val is not None:
            original_text = line[len(ts_str):].rstrip("\n")
            
            if format_mode == "pisah":
                # Cari next_ts
                next_ts = None
                for j in range(i + 1, len(parsed_lines)):
                    if parsed_lines[j][2] is not None:
                        next_ts = parsed_lines[j][2]
                        break
                
                # Offset logic
                DEFAULT_OFFSET = 0.6
                if next_ts is None:
                    new_ts_val = ts_val + DEFAULT_OFFSET
                else:
                    gap = next_ts - ts_val
                    new_ts_val = ts_val + min(DEFAULT_OFFSET, gap * 0.4)
                
                new_ts_str = _format_ts(new_ts_val)
                
                output.append(line.rstrip("\n"))
                output.append(f'{new_ts_str}{t_text}')
            elif format_mode == "id_only":
                output.append(line.rstrip("\n"))
                output_id.append(f'{ts_str}{t_text}')
            else:
                # Default: gabung
                combined_line = f'{ts_str}{original_text}  /  {t_text}'
                output.append(combined_line)
        else:
            output.append(line.rstrip("\n"))
            if format_mode == "id_only" and ts_str:
                output_id.append(line.rstrip("\n"))

    if format_mode == "id_only":
        id_path = lrc_path.replace(".lrc", ".id.lrc")
        atomic_write_text(id_path, "\n".join(output_id))
    
    atomic_write_text(lrc_path, "\n".join(output))
    _log.info("Translation OK: %s (mode=%s)", os.path.basename(lrc_path), format_mode)



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
