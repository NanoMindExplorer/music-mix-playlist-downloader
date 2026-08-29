"""
Fetch orchestrator — cari lirik sinkron via LyricsChain + post-process.

Pipeline (urutan BENAR, dijaga oleh test regresi Fase L):
    1. Build search query (normalize_track_query / override manual)
    2. Cari via LyricsChain (provider fallback + cache + negative cache)
    3. Jika gagal: iTunes "Formula Cerdas" untuk tebak judul resmi
    4. Tulis hasil via atomic_write_text
    5. process_transliteration (Romaji/Pinyin/Latin) — RETURN snapshot asli
    6. process_translation dari snapshot ASLI (bukan dari pinyin!)
    7. sync_huawei_lrc (copy ke Musiclrc folder, Termux only)
"""

from __future__ import annotations

import re
from typing import Optional

from mmpd.logger import get_logger
from mmpd.lyrics.huawei import sync_huawei_lrc
from mmpd.lyrics.translate import process_translation
from mmpd.lyrics.transliterate import process_transliteration
from mmpd.utils.fs import atomic_write_text

_log = get_logger()


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
            from mmpd.utils.matching import normalize_track_query
            clean_title = normalize_track_query(title)

        # === Strategi 1: LyricsChain (Musixmatch → LRCLIB → syncedlyrics) ===
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
                from urllib.parse import quote

                import requests
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
            snapshot = process_transliteration(lrc_path, transliterate_mode)
            source_lines = snapshot if snapshot else original_lines
            process_translation(lrc_path, translate_mode, source_lines=source_lines)
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
