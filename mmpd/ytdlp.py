"""
yt-dlp wrapper — Logger, options builder, download hook.

Sebelumnya, YTDLPLogger dan logic build ydl_opts tersebar di downloader.py.
Fase 2.2 extract ke sini agar:
- Config ydl_opts bisa di-test tanpa harus run_cli
- Logger yt-dlp terfilter konsisten
- Progress hook reusable

Public API:
    YTDLPLogger           — silent logger untuk yt-dlp (suppress noise)
    build_download_opts   — bangun ydl_opts untuk Mode 1 (download utama)
    build_retrofit_opts   — bangun ydl_opts untuk Mode 2 (metadata-only)
    build_default_postprocessors
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from mmpd.logger import get_logger

_log = get_logger()

# Kata kunci error yt-dlp yang bisa di-ignore (tidak fatal, hanya noise)
_IGNORABLE_ERROR_KEYWORDS = (
    "metadata",
    "thumbnail",
    "subtitles",
    "429",
    "too many requests",
)


class YTDLPLogger:
    """
    Custom Logger untuk membisukan log bawaan yt-dlp agar UI tetap bersih.

    yt-dlp akan memanggil method ini untuk setiap pesan:
        - debug()   → diabaikan (terlalu verbose)
        - warning() → diabaikan (terlalu noisy)
        - error()   → di-filter, hanya tampilkan yang fatal
                      (skip noise "metadata/thumbnail/429")
    """

    def debug(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        """Filter error: tampilkan hanya jika bukan noise."""
        msg_lower = msg.lower()
        if not any(k in msg_lower for k in _IGNORABLE_ERROR_KEYWORDS):
            _log.error("yt-dlp error: %s", msg)


def build_default_postprocessors(
    codec: str,
    quality: Optional[str] = None,
    embed_thumbnail: bool = True,
    is_wav: bool = False,
) -> List[Dict[str, Any]]:
    """
    Bangun list postprocessors yt-dlp untuk konversi audio + metadata + thumbnail.

    Args:
        codec:           "mp3", "flac", "wav", "best"
        quality:         Mis. "320" (kbps). None untuk default.
        embed_thumbnail: True untuk embed cover art ke audio (skip WAV)
        is_wav:          True kalau codec=="wav" — WAV tidak bisa embed thumbnail

    Returns:
        List postprocessor config untuk ydl_opts["postprocessors"]
    """
    pp: List[Dict[str, Any]] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": codec,
        }
    ]
    if quality:
        pp[0]["preferredquality"] = quality

    pp.append({"key": "FFmpegMetadata", "add_metadata": True})

    if embed_thumbnail and not is_wav:
        pp.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

    return pp


def build_download_opts(
    outtmpl: str,
    codec: str,
    quality: Optional[str] = None,
    archive_file: Optional[str] = None,
    lyrics_from_youtube_cc: bool = False,
    max_songs: Optional[int] = None,
    progress_hook: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Bangun ydl_opts untuk Mode 1 (download utama YouTube/SoundCloud).

    Args:
        outtmpl:              Template path output yt-dlp
        codec:                "mp3"/"flac"/"wav"/"best"
        quality:              Mis. "320" (kbps). None untuk default.
        archive_file:         Path file archive.txt untuk anti-duplicate.
        lyrics_from_youtube_cc: True untuk download subtitle YouTube (Mode 3).
        max_songs:            Limit jumlah lagu (playlistend). None = unlimited.
        progress_hook:        Callback untuk progress bar.

    Returns:
        Dict ydl_opts siap dipakai dengan yt_dlp.YoutubeDL(ydl_opts).
    """
    is_wav = codec == "wav"

    ydl_opts: Dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": False,
        "ignoreerrors": True,
        "geo_bypass": True,
        "sleep_interval_requests": 1,
        "sleep_interval": 2,
        "max_sleep_interval": 5,
        # Fix R13 (Fase 1): filename aman untuk semua OS
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "logger": YTDLPLogger(),
        "extract_flat": False,
    }

    if archive_file:
        ydl_opts["download_archive"] = archive_file

    # Postprocessors (konversi audio + metadata + thumbnail)
    pp = build_default_postprocessors(
        codec=codec,
        quality=quality,
        embed_thumbnail=not is_wav,
        is_wav=is_wav,
    )

    # Subtitle download untuk Mode 3 (YouTube CC lyrics)
    if lyrics_from_youtube_cc:
        ydl_opts["writesubtitles"] = True
        ydl_opts["writeautomaticsub"] = True
        ydl_opts["subtitleslangs"] = ["id", "en", "ja", "ko", "all"]
        pp.append({"key": "FFmpegSubtitlesConvertor", "format": "lrc"})

    ydl_opts["postprocessors"] = pp

    if max_songs:
        ydl_opts["playlistend"] = max_songs

    if progress_hook:
        ydl_opts["progress_hooks"] = [progress_hook]

    # Wajib tulis thumbnail jika akan di-embed
    if not is_wav:
        ydl_opts["writethumbnail"] = True

    return ydl_opts


def build_retrofit_opts(
    outtmpl: str,
    lyrics_from_youtube_cc: bool = False,
) -> Dict[str, Any]:
    """
    Bangun ydl_opts khusus untuk Mode 2 (Retrofit) — skip download audio,
    hanya ambil metadata + thumbnail + subtitle.

    Args:
        outtmpl:                Template path untuk file sementara
        lyrics_from_youtube_cc: True untuk download subtitle (Mode 3)

    Returns:
        Dict ydl_opts untuk Retrofit mode.
    """
    ydl_opts: Dict[str, Any] = {
        "format": "bestaudio/best",
        "skip_download": True,
        "writethumbnail": True,
        "sleep_interval_requests": 1,
        "sleep_interval": 3,
        "max_sleep_interval": 8,
        "retries": 5,
        "file_access_retries": 5,
        "fragment_retries": 5,
        "outtmpl": outtmpl,
        # Fix R13 (Fase 1): filename aman lintas-platform
        "restrictfilenames": True,
        "quiet": True,
        "no_warnings": True,
        "logger": YTDLPLogger(),
    }

    if lyrics_from_youtube_cc:
        ydl_opts["writesubtitles"] = True
        ydl_opts["writeautomaticsub"] = True
        ydl_opts["subtitleslangs"] = ["id", "en", "ja", "ko", "all"]
        ydl_opts["postprocessors"] = [{"key": "FFmpegSubtitlesConvertor", "format": "lrc"}]

    return ydl_opts


def default_download_hook(progress, main_task):
    """
    Factory: buat download hook callback untuk Progress bar rich.

    Args:
        progress: rich.Progress instance
        main_task: task ID di Progress

    Returns:
        Function yang bisa dipass ke ydl_opts["progress_hooks"].
    """

    def hook(d: Dict[str, Any]) -> None:
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            filename = d.get("filename", "")
            # Truncate filename untuk display
            display_name = filename.rsplit("/", 1)[-1][:32] if filename else "Lagu"
            progress.update(
                main_task,
                description=f"[cyan]Mengunduh: [bold white]{display_name}",
                total=total if total > 0 else None,
                completed=downloaded,
            )
        elif status == "finished":
            filename = d.get("filename", "")
            display_name = filename.rsplit("/", 1)[-1][:32] if filename else "Lagu"
            progress.update(
                main_task,
                description=f"[green]Memproses Media: [bold white]{display_name}",
                total=None,
                completed=0,
            )

    return hook
