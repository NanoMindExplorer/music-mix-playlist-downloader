"""
FFmpeg wrapper — command execution yang aman dari injection.

Sebelum Fase 1, kode lama pakai os.system(cmd) dengan string interpolation
dari path filesystem user → command injection. Fase 1 sudah fix dengan
subprocess.run() inline. Fase 2.2 extract logic ini ke sini supaya bisa
di-test terpisah dan dipakai ulang.

Functions:
    inject_cover_to_audio  - sisipkan cover art (jpg/webp) ke file audio
    check_ffmpeg_available  - cek apakah ffmpeg ada di PATH
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from mmpd.logger import get_logger

_log = get_logger()


def check_ffmpeg_available() -> bool:
    """Cek apakah binary ffmpeg tersedia di PATH."""
    return shutil.which("ffmpeg") is not None


def inject_cover_to_audio(
    audio_path: str,
    cover_path: str,
    output_path: str,
    audio_format: str = "mp3",
) -> bool:
    """
    Sisipkan cover art ke dalam file audio (MP3/FLAC) menggunakan FFmpeg.

    Args:
        audio_path:   Path file audio input (mp3/flac)
        cover_path:   Path file cover art (jpg/webp/png)
        output_path:  Path file audio output (akan dibuat)
        audio_format: Format audio — "mp3" atau "flac" (menentukan flag FFmpeg)

    Returns:
        True jika berhasil, False jika gagal.

    Security:
        Memakai subprocess.run() dengan list argumen — TIDAK ada shell
        interpolation, aman dari command injection via filename.

    Raises:
        Tidak ada — semua exception ditangani dan di-log.
    """
    if not check_ffmpeg_available():
        _log.error("FFmpeg tidak ditemukan di PATH")
        return False

    # Build command list sesuai format
    if audio_format.lower() == "mp3":
        cmd: List[str] = [
            "ffmpeg", "-y", "-v", "quiet",
            "-i", audio_path,
            "-i", cover_path,
            "-map", "0:0", "-map", "1:0",
            "-c", "copy",
            "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            output_path,
        ]
    elif audio_format.lower() == "flac":
        cmd = [
            "ffmpeg", "-y", "-v", "quiet",
            "-i", audio_path,
            "-i", cover_path,
            "-map", "0:0", "-map", "1:0",
            "-c", "copy",
            "-disposition:v", "attached_pic",
            output_path,
        ]
    else:
        _log.error("Format tidak didukung: %s (hanya mp3/flac)", audio_format)
        return False

    _log.debug("FFmpeg inject cover: %s → %s", audio_path, output_path)
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        _log.info("Cover art injected: %s", Path(output_path).name)
        return True
    except subprocess.CalledProcessError as e:
        _log.error(
            "FFmpeg gagal untuk %s (exit %d): %s",
            Path(audio_path).name,
            e.returncode,
            (e.stderr or "").strip()[:500],
        )
        return False
    except FileNotFoundError:
        _log.error("FFmpeg binary tidak ditemukan saat eksekusi")
        return False
    except Exception as e:
        _log.error("Error tak terduga saat injeksi cover %s: %s", audio_path, e)
        return False


def convert_audio(
    input_path: str,
    output_path: str,
    codec: str = "mp3",
    bitrate: Optional[str] = None,
) -> bool:
    """
    Convert audio ke format lain via FFmpeg (umumnya sudah ditangani yt-dlp
    postprocessor, tapi disediakan untuk Retrofit mode yang butuh re-encode).

    Args:
        input_path:  Path audio input
        output_path: Path audio output
        codec:       "mp3", "flac", "wav", "aac"
        bitrate:     Mis. "320k" — None untuk default

    Returns:
        True jika berhasil, False jika gagal.
    """
    if not check_ffmpeg_available():
        _log.error("FFmpeg tidak ditemukan")
        return False

    cmd = [
        "ffmpeg", "-y", "-v", "quiet",
        "-i", input_path,
        "-vn",  # drop video stream
        "-acodec", codec if codec != "best" else "copy",
    ]
    if bitrate and codec != "best":
        cmd.extend(["-b:a", bitrate])
    cmd.append(output_path)

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except Exception as e:
        _log.error("Convert audio gagal %s → %s: %s", input_path, output_path, e)
        return False

def crop_cover_to_square(input_path: str, output_path: str) -> bool:
    if not check_ffmpeg_available():
        return False
    cmd = ["ffmpeg", "-y", "-v", "quiet", "-i", input_path, "-vf", "crop='min(iw,ih)':'min(iw,ih)'", output_path]
    try:
        subprocess.run(cmd, check=True)
        return True
    except Exception:
        return False
