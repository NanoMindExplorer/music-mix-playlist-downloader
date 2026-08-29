"""
Title matching & query cleaning utilities.

Berisi:
- normalize_track_query: SATU fungsi normalisasi query pencarian lagu
  (P0/Fase L — sebelumnya duplikat & tidak konsisten antara
  `matching.clean_search_query` dan `TrackInfo.clean_search_query`)
- clean_search_query: alias backward-compat ke normalize_track_query
- fuzzy_match: wrapper rapidfuzz untuk matching lagu dengan lirik
- normalize_title: lower-case + trim + collapse whitespace
- TrackIdentity: pecah identitas track (artist, title, is_cover, lang)

Dipakai oleh:
- mmpd.lyrics (untuk pencarian lirik yang akurat)
- mmpd.modes.organizer (untuk match file .lrc dengan .mp3)
- mmpd.lyrics_providers (via TrackInfo.clean_search_query)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
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

# Pola deteksi lagu cover (multi-bahasa) — dipakai TrackIdentity.is_cover
_COVER_RE = re.compile(
    r"(?i)\b(cover|covered|version|歌ってみた|翻唱|カバー|커버|คัฟเวอร์|flukie)\b"
)

# Aksara CJK/Thai/Arab untuk deteksi bahasa kasar
_HIRAGANA_KATAKANA_RE = re.compile(r"[぀-ヿ]")
_HAN_RE = re.compile(r"[一-鿿]")
_HANGUL_RE = re.compile(r"[가-힣]")
_THAI_RE = re.compile(r"[ก-๛]")
_KANA_OK = True  # marker agar mudah cari di grep

# OpenCC singleton (P1/Fase R — dulu dibuat baru pada SETIAP panggilan)
_OPENCC_CONVERTER = None


def _get_opencc():
    """Singleton OpenCC t2s converter. Return None kalau opencc tak terinstal."""
    global _OPENCC_CONVERTER
    if _OPENCC_CONVERTER is None:
        try:
            import opencc
            _OPENCC_CONVERTER = opencc.OpenCC("t2s")
        except Exception:
            _OPENCC_CONVERTER = False  # marker: pernah dicoba, tidak tersedia
    return _OPENCC_CONVERTER or None


def normalize_track_query(title: str, artist: Optional[str] = None) -> str:
    """
    Normalisasi query pencarian lagu — SATU-SATUNYA implementasi (P0/Fase L).

    Sebelumnya ada DUA implementasi yang berbeda hasilnya:
      - mmpd.utils.matching.clean_search_query (bracket + promo + OpenCC)
      - mmpd.types.TrackInfo.clean_search_query (regex lebih sempit, tanpa OpenCC)
    Provider lirik dapat query berbeda tergantung jalur kode → hasil pencarian
    tidak konsisten. Sekarang keduanya mendelegasi ke fungsi ini.

    Langkah:
        1. Gabung "artist title" (artist opsional, di depan)
        2. Hapus [bracket], (parenthetical), 【】,（），「」，『』，《》
        3. Hapus kata kunci promo (Official, MV, Cover, 翻唱, dll.)
        4. Collapse spasi ganda + trim
        5. Normalisasi Traditional → Simplified Chinese (OpenCC t2s, singleton)

    Contoh:
        ("JUSTadICE", "[Rainych]")                       → "JUSTadICE"
        ("Hello", "Adele", )  + "(Official Music Video)" → "Adele Hello"
        ("聽海", "張惠妹")                                → "张惠妹 听海"
    """
    if not title:
        return ""
    combined = f"{artist} {title}" if artist and artist.strip() else title

    # Hapus [bracket], (parenthetical), 【japanese bracket】
    result = _BRACKET_RE.sub("", combined)
    # Hapus kata kunci promo
    result = _PROMO_RE.sub("", result)
    # Trim + collapse multiple spaces
    result = _MULTI_SPACE_RE.sub(" ", result).strip()

    # Normalisasi OpenCC (Traditional → Simplified) via singleton
    converter = _get_opencc()
    if converter is not None:
        try:
            result = converter.convert(result)
        except Exception:
            pass

    return result


# Backward-compat alias: dulu signature-nya (title) saja.
def clean_search_query(title: str) -> str:
    """Alias backward-compat → normalize_track_query(title)."""
    return normalize_track_query(title)


def detect_query_lang(text: str) -> str:
    """Deteksi bahasa kasar dari teks (untuk TrackIdentity.lang)."""
    if not text:
        return "unknown"
    if _HIRAGANA_KATAKANA_RE.search(text):
        return "ja"
    if _HANGUL_RE.search(text):
        return "ko"
    if _THAI_RE.search(text):
        return "th"
    if _HAN_RE.search(text):
        return "zh"
    return "latin"


@dataclass(frozen=True)
class TrackIdentity:
    """
    Identitas track yang sudah dipecah (P1/Fase L).

    Field:
        artist:  nama artist (bisa kosong kalau tidak terdeteksi)
        title:   judul bersih (tanpa promo/bracket)
        is_cover: True kalau judul mengandung penanda cover
                  (cover/翻唱/歌ってみた/커버/คัฟเวอร์/flukie)
        lang:    bahasa kasar ("ja"/"zh"/"ko"/"th"/"latin")
    """

    artist: Optional[str] = None
    title: str = ""
    is_cover: bool = False
    lang: str = "latin"

    @classmethod
    def from_raw_title(cls, raw_title: str, artist: Optional[str] = None) -> TrackIdentity:
        """Pecah judul mentah (mis. 'JUSTadICE (Official Music Video)') jadi identitas bersih."""
        is_cover = bool(_COVER_RE.search(raw_title or ""))
        clean = normalize_track_query(raw_title, artist=None) if artist else normalize_track_query(raw_title)
        lang = detect_query_lang(raw_title or "")
        return cls(artist=artist, title=clean, is_cover=is_cover, lang=lang)

    def search_query(self) -> str:
        """Query pencarian lengkap: 'artist title'."""
        return normalize_track_query(self.title, self.artist)


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
    converter = _get_opencc()
    if converter is not None:
        source_comp = converter.convert(source)
        candidates_comp = [converter.convert(c) for c in candidates]
    else:
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


def reset_matching_singletons() -> None:
    """Reset singleton OpenCC (untuk testing)."""
    global _OPENCC_CONVERTER
    _OPENCC_CONVERTER = None
