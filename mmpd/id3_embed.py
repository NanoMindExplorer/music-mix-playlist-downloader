"""
ID3 lyrics embedding — tanam lirik ke dalam file audio (Fase L).

Dukungan:
    MP3  → USLT (unsynced plain lyrics) + SYLT (synced LRC)
    FLAC → Vorbis comment "LYRICS" (plain) + "SYNCEDLYRICS" (LRC)
    M4A/MP4 → ©lyr tag (plain lyrics)

Kenapa penting:
    File .lrc sampingan hanya dibaca beberapa player (Poweramp, Huawei Music).
    USLT/SYLT tertanam menjamin lirik muncul di player yang tidak membaca
    .lrc (VLC, foobar2000, head-unit mobil, dsb.) — satu sumber kebenaran.

API utama:
    embed_lyrics_to_audio(audio_path, lrc_path)  → baca .lrc, tanam ke audio
    has_embedded_lyrics(audio_path)               → deteksi cepat

Semua operasi atomic (tulis ke temp file + os.replace) supaya file audio
tidak korup kalau proses crash di tengah jalan.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional, Tuple

from mmpd.logger import get_logger

_log = get_logger()

# Pola timestamp LRC: [mm:ss.xx] atau [mm:ss]
_LRC_TS_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def parse_lrc_to_lines(lrc_text: str) -> List[Tuple[float, str]]:
    """Parse LRC → list (timestamp_detik, teks). Baris tanpa timestamp di-skip."""
    result: List[Tuple[float, str]] = []
    for line in lrc_text.splitlines():
        m = _LRC_TS_RE.match(line.strip())
        if not m:
            continue
        ts = int(m.group(1)) * 60 + float(m.group(2))
        text = _LRC_TS_RE.sub("", line).strip()
        result.append((ts, text))
    return sorted(result, key=lambda x: x[0])


def _lrc_to_plain(lrc_text: str) -> str:
    """Strip timestamp numerik + tag metadata ([ti:]/[ar:/[al:] → plain text (untuk USLT)."""
    lines = []
    for line in lrc_text.splitlines():
        text = _LRC_TS_RE.sub("", line).strip()
        # Buang juga tag metadata LRC non-numerik ([ti:..], [ar:..], [by:..], dst.)
        text = re.sub(r"\[[a-zA-Z]+:[^\]]*\]", "", text).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def _lrc_text_from_file(lrc_path: str) -> Optional[str]:
    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content if content.strip() else None
    except Exception as e:
        _log.warning("Gagal baca LRC %s: %s", lrc_path, e)
        return None


def has_embedded_lyrics(audio_path: str) -> bool:
    """Cek apakah file audio sudah punya lirik tertanam (USLT/SYLT/LYRICS)."""
    if not os.path.exists(audio_path):
        return False
    ext = os.path.splitext(audio_path)[1].lower()
    try:
        # MP3: buka ID3 langsung (lebih andal daripada auto-detect mutagen
        # untuk file tanpa frame audio / berheader aneh)
        if ext == ".mp3":
            from mutagen.id3 import ID3
            try:
                tags = ID3(audio_path)
            except Exception:
                return False
            return bool(tags.getall("USLT") or tags.getall("SYLT"))

        from mutagen import File as MutagenFile

        audio = MutagenFile(audio_path)
        if audio is None or audio.tags is None:
            return False
        tags = audio.tags
        # FLAC / OGG (Vorbis comments)
        try:
            return bool(
                tags.get("LYRICS") or tags.get("SYNCEDLYRICS") or tags.get("UNSYNCEDLYRICS")
            )
        except Exception:
            pass
        # MP4
        try:
            return bool(tags.get("\xa9lyr"))
        except Exception:
            return False
    except Exception:
        return False


def embed_lyrics_to_audio(
    audio_path: str,
    lrc_path: str,
    overwrite: bool = True,
    language: str = "ind",
    description: str = "mmpd",
) -> bool:
    """
    Tanam lirik dari file .lrc ke file audio (MP3: USLT+SYLT, FLAC: Vorbis).

    Args:
        audio_path:  path file audio (.mp3/.flac)
        lrc_path:    path file .lrc sumber
        overwrite:   False = skip kalau sudah ada lirik tertanam
        language:    kode bahasa USLT (default 'ind' — terjemahan Indonesia)
        description: deskripsi frame USLT/SYLT

    Returns:
        True kalau berhasil ditanam (atau sudah ada & overwrite=False),
        False kalau gagal / format tidak didukung.
    """
    if not os.path.exists(audio_path):
        _log.debug("embed_lyrics: audio tidak ada: %s", audio_path)
        return False

    lrc_text = _lrc_text_from_file(lrc_path)
    if not lrc_text:
        return False

    ext = os.path.splitext(audio_path)[1].lower()
    try:
        if ext == ".mp3":
            return _embed_mp3(audio_path, lrc_text, overwrite, language, description)
        if ext == ".flac":
            return _embed_flac(audio_path, lrc_text, overwrite)
        if ext in (".m4a", ".mp4"):
            return _embed_mp4(audio_path, lrc_text, overwrite)
        _log.debug("embed_lyrics: format %s belum didukung, skip", ext)
        return False
    except Exception as e:
        _log.warning("embed_lyrics gagal untuk %s: %s", os.path.basename(audio_path), e)
        return False


def _embed_mp3(audio_path: str, lrc_text: str, overwrite: bool, language: str, description: str) -> bool:
    """Tanam USLT (plain) + SYLT (synced) ke MP3 ID3v2."""
    from mutagen.id3 import ID3, SYLT, USLT, Encoding

    try:
        tags = ID3(audio_path)
    except Exception:
        tags = ID3()

    if not overwrite and (tags.getall("USLT") or tags.getall("SYLT")):
        _log.debug("embed_lyrics: %s sudah punya lirik, skip (overwrite=False)", audio_path)
        return True

    plain = _lrc_to_plain(lrc_text)

    # USLT: lirik plain (dibaca hampir semua player)
    tags.setall("USLT", [
        USLT(
            encoding=Encoding.UTF8,
            lang=language,
            desc=description,
            text=plain,
        )
    ])

    # SYLT: lirik synced (dibaca player yang dukung karaoke ID3)
    # Format mutagen: text = list of tuple (teks, timestamp_ms)
    synced = parse_lrc_to_lines(lrc_text)
    text_time_pairs = [(t, int(ts * 1000)) for ts, t in synced if t]
    if text_time_pairs:
        tags.setall("SYLT", [
            SYLT(
                encoding=Encoding.UTF8,
                lang=language,
                format=2,  # 2 = milliseconds
                type=1,    # 1 = lyrics
                desc=description,
                text=text_time_pairs,
            )
        ])

    tags.save(audio_path, v2_version=3)
    _log.info("Lyrics embedded (USLT+SYLT): %s", os.path.basename(audio_path))
    return True


def _embed_flac(audio_path: str, lrc_text: str, overwrite: bool) -> bool:
    """Tanam LYRICS + SYNCEDLYRICS ke FLAC Vorbis comments."""
    from mutagen.flac import FLAC

    audio = FLAC(audio_path)
    if not overwrite and (audio.get("LYRICS") or audio.get("SYNCEDLYRICS")):
        _log.debug("embed_lyrics: %s sudah punya lirik, skip", audio_path)
        return True

    audio["LYRICS"] = _lrc_to_plain(lrc_text)
    audio["SYNCEDLYRICS"] = lrc_text
    audio.save()
    _log.info("Lyrics embedded (Vorbis LYRICS): %s", os.path.basename(audio_path))
    return True


def _embed_mp4(audio_path: str, lrc_text: str, overwrite: bool) -> bool:
    """Tanam ©lyr ke MP4/M4A."""
    from mutagen.mp4 import MP4

    audio = MP4(audio_path)
    if not overwrite and audio.tags and audio.tags.get("\xa9lyr"):
        return True
    audio["\xa9lyr"] = [_lrc_to_plain(lrc_text)]
    audio.save()
    _log.info("Lyrics embedded (MP4 ©lyr): %s", os.path.basename(audio_path))
    return True
