"""
Title matching & query cleaning utilities.

Berisi:
- clean_search_query: hapus [bracket], (parenthetical), 【japanese】, dan
  kata kunci promo (Official, MV, Cover, dll.)
- fuzzy_match: wrapper rapidfuzz untuk matching lagu dengan lirik
- normalize_title: lower-case + trim + collapse whitespace

Dipakai oleh:
- mmpd.lyrics (untuk pencarian lirik yang akurat)
- mmpd.modes.organizer (untuk match file .lrc dengan .mp3)
- mmpd.lyrics_providers (via TrackInfo.clean_search_query, sudah ada di Fase 2.1)
"""

from __future__ import annotations

import re
from typing import Optional

# Regex pre-compiled untuk performance
_BRACKET_RE = re.compile(r"\[.*?\]|\(.*?\)|【.*?】|（.*?）|「.*?」|『.*?』|《.*?》")
_PROMO_RE = re.compile(
    r"(?i)\b("
    r"official|music video|mv|lyrics?|video|audio|cover|hd|hq|4k|explicit|clean|"
    r"lirik( lagu)?|terbaru|resmi|karaoke|full album|live( performance)?|"
    r"歌ってみた|公式|フル|歌詞|官方|翻唱|歌词|完整版|뮤직비디오|커버|가사|공식|เนื้อเพลง|คัฟเวอร์"
    r")\b"
)
_MULTI_SPACE_RE = re.compile(r"\s+")


def clean_search_query(title: str) -> str:
    """
    Bersihkan judul untuk pencarian lirik.

    Contoh:
        "[Rainych] JUSTadICE (Official Music Video)" → "JUSTadICE"
        "Adele - Hello (Lyric Video) [HD]"            → "Adele - Hello"
        "【東方】Vocal Cover"                          → "Vocal Cover"

    Args:
        title: Judul mentah dari YouTube/Spotify/file

    Returns:
        Judul bersih siap dipakai untuk search.
    """
    if not title:
        return ""

    # Hapus [bracket], (parenthetical), 【japanese bracket】
    result = _BRACKET_RE.sub("", title)
    # Hapus kata kunci promo
    result = _PROMO_RE.sub("", result)
    # Trim + collapse multiple spaces
    result = _MULTI_SPACE_RE.sub(" ", result).strip()
    return result


def normalize_title(title: str) -> str:
    """Normalize untuk comparison: lowercase + collapse whitespace + trim."""
    if not title:
        return ""
    return _MULTI_SPACE_RE.sub(" ", title).strip().lower()


def fuzzy_match(
    source: str,
    candidates: list[str],
    threshold: int = 50,
) -> Optional[str]:
    """
    Cari best match dari candidates berdasarkan fuzzy string matching.
    """
    try:
        import opencc
        converter = opencc.OpenCC('t2s')
        source_comp = converter.convert(source)
        candidates_comp = [converter.convert(c) for c in candidates]
    except ImportError:
        source_comp = source
        candidates_comp = candidates

    try:
        from rapidfuzz import fuzz
    except ImportError:
        # Fallback: simple equality (lower case)
        norm_source = normalize_title(source_comp)
        for idx, c in enumerate(candidates_comp):
            if norm_source == normalize_title(c):
                return candidates[idx]
        return None

    if not candidates:
        return None

    norm_source = normalize_title(source_comp)
    best_match: Optional[str] = None
    best_score = 0

    for idx, candidate in enumerate(candidates_comp):
        norm_candidate = normalize_title(candidate)
        score = fuzz.ratio(norm_source, norm_candidate)
        if score > best_score:
            best_score = score
            best_match = candidates[idx]

    if best_score >= threshold:
        return best_match
    return None


def extract_extension(filename: str) -> str:
    """Extract extension (lowercase, tanpa dot). Mis. 'Song.MP3' → 'mp3'."""
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower()


def strip_extension(filename: str) -> str:
    """Hapus extension dari filename. Mis. 'song.mp3' → 'song'."""
    if "." not in filename:
        return filename
    return filename.rsplit(".", 1)[0]
