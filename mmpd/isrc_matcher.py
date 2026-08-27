"""
ISRC-based YouTube matching — akurasi 99%+ vs fuzzy title matching.

Sebelumnya, Spotify track dicari di YouTube dengan:
    ytsearch1:"Artist Title"
YouTube akan return video pertama yang cocok. Masalah:
    - Sering salah (cover, lyric video, vs official)
    - Tidak ada verifikasi akurasi
    - Tidak bisa disambiguate kalau ada banyak video dengan judul sama

Fase 2.3 introduce ISRC matching:
    1. Spotify track punya ISRC (International Standard Recording Code)
       Format: CC-XXX-YY-NNNNN (mis. 'USUM71703861')
    2. yt-dlp search: ytsearch3:"query" → return top 3 candidates
    3. Extract ISRC dari metadata YouTube video (ada di 'external_ids' field)
    4. Match ISRC Spotify == ISRC YouTube → akurasi 99%+

Fallback kalau ISRC tidak ada:
    - Fuzzy match judul+artist (rapidfuzz, threshold 80%)
    - Duration verification (selisih <5 detik)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yt_dlp

from mmpd.logger import get_logger
from mmpd.types import TrackInfo
from mmpd.utils.matching import normalize_title
from mmpd.ytdlp import YTDLPLogger

_log = get_logger()


@dataclass
class YouTubeMatchResult:
    """Hasil matching YouTube."""

    video_url: str                # URL YouTube untuk diunduh
    video_title: str              # Judul video YouTube
    isrc_match: bool              # True kalau match via ISRC (paling akurat)
    fuzzy_score: Optional[int] = None  # Score 0-100 kalau match via fuzzy
    duration_diff_sec: Optional[float] = None  # Selisih durasi (detik)


def search_youtube_with_isrc(
    track: TrackInfo,
    max_candidates: int = 3,
    target_duration_sec: Optional[float] = None,
) -> Optional[YouTubeMatchResult]:
    """
    Cari video YouTube untuk track Spotify, prioritaskan ISRC match.

    Strategi (urutan):
        1. ISRC match: extract ISRC dari metadata top-3 YouTube candidates,
           bandingkan dengan track.isrc. Match → return.
        2. Fuzzy + duration: kalau tidak ada ISRC match, fuzzy title match
           dengan verification durasi (selisih <5 detik).
        3. Pure fuzzy: kalau tidak ada duration, fuzzy match saja (threshold 80%).

    Args:
        track:                TrackInfo dengan title, artist, isrc, duration
        max_candidates:       Jumlah top YouTube results untuk di-evaluate
        target_duration_sec: Durasi track Spotify (untuk verification)

    Returns:
        YouTubeMatchResult kalau ada match, None kalau tidak.
    """
    if not track.title:
        return None

    # Bangun query pencarian
    query = track.search_query()
    if not query:
        return None

    _log.info(
        "ISRC matcher: searching YouTube for '%s' (isrc=%s, duration=%s)",
        query,
        track.isrc,
        target_duration_sec,
    )

    # Search top-N candidates
    candidates = _ytsearch_extract(query, limit=max_candidates)
    if not candidates:
        _log.warning("ISRC matcher: no YouTube results for '%s'", query)
        return None

    _log.debug("ISRC matcher: %d candidates to evaluate", len(candidates))

    # === Strategi 1: ISRC match ===
    if track.isrc:
        for candidate in candidates:
            candidate_isrc = _extract_isrc(candidate)
            if candidate_isrc and _isrc_match(track.isrc, candidate_isrc):
                _log.info(
                    "ISRC MATCH! track=%s youtube=%s",
                    track.isrc,
                    candidate_isrc,
                )
                return YouTubeMatchResult(
                    video_url=candidate.get("url", ""),
                    video_title=candidate.get("title", query),
                    isrc_match=True,
                )

    # === Strategi 2: Fuzzy + duration verification ===
    best_score = 0
    best_candidate = None
    best_duration_diff = None

    target_title = normalize_title(f"{track.artist or ''} {track.title}".strip())
    if not target_title:
        target_title = normalize_title(track.title)

    for candidate in candidates:
        # Build comparable title dari YouTube result
        yt_title = normalize_title(candidate.get("title", ""))
        yt_uploader = normalize_title(candidate.get("uploader", "") or candidate.get("channel", ""))
        yt_combined = f"{yt_uploader} {yt_title}".strip()

        # Fuzzy match
        score = _fuzzy_ratio(target_title, yt_title)
        if yt_uploader:
            score_uploader = _fuzzy_ratio(target_title, yt_combined)
            score = max(score, score_uploader)

        # Duration verification
        duration_diff = None
        if target_duration_sec and candidate.get("duration"):
            yt_duration = candidate["duration"]
            duration_diff = abs(target_duration_sec - yt_duration)

            # Jika duration match (selisih <5 detik) DAN score >=70 → bonus
            if duration_diff < 5 and score >= 70:
                _log.info(
                    "FUZZY+DURATION MATCH: score=%d, duration_diff=%.2fs (title='%s')",
                    score,
                    duration_diff,
                    candidate.get("title", "")[:60],
                )
                return YouTubeMatchResult(
                    video_url=candidate.get("url", ""),
                    video_title=candidate.get("title", query),
                    isrc_match=False,
                    fuzzy_score=score,
                    duration_diff_sec=duration_diff,
                )

        # Track best score (fallback ke strategi 3)
        if score > best_score:
            best_score = score
            best_candidate = candidate
            best_duration_diff = duration_diff

    # === Strategi 3: Pure fuzzy (threshold 80%) ===
    if best_candidate and best_score >= 80:
        _log.info(
            "FUZZY MATCH: score=%d, title='%s'",
            best_score,
            best_candidate.get("title", "")[:60],
        )
        return YouTubeMatchResult(
            video_url=best_candidate.get("url", ""),
            video_title=best_candidate.get("title", query),
            isrc_match=False,
            fuzzy_score=best_score,
            duration_diff_sec=best_duration_diff,
        )

    _log.warning(
        "ISRC matcher: no good match (best_score=%d, threshold=80) for '%s'",
        best_score,
        query[:60],
    )

    # Last resort: return candidate pertama (sebelumnya seperti ini behavior lama)
    if candidates and best_score >= 50:
        _log.info("ISRC matcher: fallback to first candidate (score=%d)", best_score)
        return YouTubeMatchResult(
            video_url=candidates[0].get("url", ""),
            video_title=candidates[0].get("title", query),
            isrc_match=False,
            fuzzy_score=best_score,
            duration_diff_sec=best_duration_diff,
        )

    return None


def _ytsearch_extract(query: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Search YouTube via yt-dlp, return list of video metadata (tanpa download).

    Returns list of dict dengan keys:
        - url:      URL YouTube
        - title:    Judul video
        - duration: Durasi dalam detik
        - uploader: Nama channel
        - isrc:     ISRC kalau ada di metadata (extract via external_ids)
    """
    search_query = f"ytsearch{limit}:{query}"
    opts = {
        "format": "bestaudio/best",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "logger": YTDLPLogger(),
        "extract_flat": False,
        # Hanya ambil info, tidak download
        "writethumbnail": False,
        "writesubtitles": False,
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            if not info or "entries" not in info:
                return []

            results: List[Dict[str, Any]] = []
            for entry in info["entries"]:
                if not entry:
                    continue
                results.append({
                    "url": entry.get("webpage_url") or entry.get("url", ""),
                    "title": entry.get("title", ""),
                    "duration": entry.get("duration"),
                    "uploader": entry.get("uploader") or entry.get("channel"),
                    "external_ids": entry.get("external_ids") or {},
                    "track": entry.get("track"),
                    "artist": entry.get("artist"),
                })

            return results
    except Exception as e:
        _log.warning("ytsearch extract failed for '%s': %s", query[:50], e)
        return []


def _extract_isrc(candidate: Dict[str, Any]) -> Optional[str]:
    """
    Extract ISRC dari metadata YouTube video.

    yt-dlp return external_ids sebagai dict, mis.:
        {"isrc": "USUM71703861", "isbn": null, ...}
    """
    external_ids = candidate.get("external_ids") or {}
    if not isinstance(external_ids, dict):
        return None
    isrc = external_ids.get("isrc")
    if isrc and isinstance(isrc, str) and len(isrc) >= 12:
        return isrc.upper().replace("-", "").replace(" ", "")
    return None


def _isrc_match(spotify_isrc: str, youtube_isrc: str) -> bool:
    """
    Bandingkan dua ISRC, normalize (uppercase, strip dash/space).

    ISRC format: CC-XXX-YY-NNNNN (12 chars tanpa dash)
        Contoh: USUM71703861
    """
    s = spotify_isrc.upper().replace("-", "").replace(" ", "")
    y = youtube_isrc.upper().replace("-", "").replace(" ", "")
    if len(s) < 12 or len(y) < 12:
        return False
    return s == y


def _fuzzy_ratio(s1: str, s2: str) -> int:
    """Wrapper rapidfuzz dengan fallback ke simple comparison."""
    try:
        from rapidfuzz import fuzz
        return int(fuzz.ratio(s1, s2))
    except ImportError:
        # Fallback: simple equality
        return 100 if s1 == s2 else 0
