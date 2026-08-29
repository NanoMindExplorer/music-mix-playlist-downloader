"""
mmpd.lyrics — Lyrics Engine pipeline package (Fase A).

Sebelumnya satu file 35KB (mmpd/lyrics.py). Sekarang dipecah per tanggung
jawab supaya mudah dirawat dan di-test:

    mmpd.lyrics.huawei        — sync_huawei_lrc (Musiclrc Termux/Huawei)
    mmpd.lyrics.transliterate — detect_script + process_transliteration
    mmpd.lyrics.translate     — process_translation (Google → MyMemory)
    mmpd.lyrics.lrc_format    — parse/render/write bilingual (gabung/pisah/id_only)
    mmpd.lyrics.fetch         — fetch_synced_lyrics (orchestrator)

Import path LAMA tetap berfungsi 100% (backward compatible):

    from mmpd.lyrics import (
        fetch_synced_lyrics,        # ← sama seperti sebelumnya
        process_translation,
        process_transliteration,
        sync_huawei_lrc,
        detect_script,
        is_already_bilingual,
    )
"""

from __future__ import annotations

# Public API (dipakai downloader.py, modes/*, tests)
from mmpd.lyrics.fetch import fetch_synced_lyrics
from mmpd.lyrics.huawei import sync_huawei_lrc
from mmpd.lyrics.lrc_format import (
    _looks_like_failed_translation,
    _strip_lrc_text,
    _write_bilingual_lrc,
    format_ts,
    is_already_bilingual,
    parse_lrc_lines,
    parse_ts,
    render_lrc,
    write_bilingual_from_lines,
)
from mmpd.lyrics.translate import (
    _detect_source_lang,
    _translate_via_api,
    process_translation,
)
from mmpd.lyrics.transliterate import (
    detect_script,
    process_transliteration,
)

__all__ = [
    # Internal (dipakai test suite lama — jangan hapus)
    "_detect_source_lang",
    "_looks_like_failed_translation",
    "_strip_lrc_text",
    "_translate_via_api",
    "_write_bilingual_lrc",
    "detect_script",
    "fetch_synced_lyrics",
    "format_ts",
    "is_already_bilingual",
    "parse_lrc_lines",
    "parse_ts",
    "process_translation",
    "process_transliteration",
    "render_lrc",
    "sync_huawei_lrc",
    "write_bilingual_from_lines",
]
