"""
Mode 3: Auto-Organizer (Pengatur Otomatis).

Skenario: User download lirik (.lrc) manual di internet, taruh di folder
Downloads secara berantakan. Mode ini akan:
    1. Cari file .lrc di Downloads root
    2. Match dengan file .mp3 di Downloads root (rapidfuzz)
    3. Rename .lrc agar sama persis dengan .mp3
    4. Pindahkan .mp3 ke folder Music, .lrc ke folder Musiclrc (Huawei style)
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from mmpd.config import get_config
from mmpd.logger import get_logger
from mmpd.ui import ask_confirm, console
from mmpd.utils.matching import fuzzy_match

_log = get_logger()


def run_organizer() -> None:
    """Jalankan Mode 3: Auto-Organizer."""
    console.print(f"\n[bold cyan]📁 Mode 3: Pengatur Otomatis (Auto-Organizer)[/bold cyan]")
    console.print(
        "[white]Sistem akan mencari lagu & lirik yang Anda unduh secara manual di folder "
        "Downloads, lalu menyamakan namanya dan memindahkannya ke folder Huawei Music "
        "secara otomatis![/white]\n"
    )

    config = get_config()

    # Tentukan path berdasarkan environment
    if config.is_termux:
        downloads_dir = str(Path.home() / "storage" / "downloads")
        music_dir = str(Path.home() / "storage" / "shared" / "Music")
    else:
        downloads_dir = str(Path.home() / "Downloads")
        music_dir = os.path.join(downloads_dir, "Music")

    lrc_dir = os.path.join(music_dir, "Musiclrc")

    if not os.path.exists(downloads_dir):
        console.print("[bold red]❌ Folder Downloads tidak ditemukan![/bold red]")
        return

    # Cari file mp3 dan lrc di root Downloads
    try:
        all_files = os.listdir(downloads_dir)
    except OSError as e:
        console.print(f"[bold red]❌ Tidak bisa baca folder Downloads: {e}[/bold red]")
        return

    mp3_files = [f for f in all_files if f.lower().endswith(".mp3")]
    lrc_files = [f for f in all_files if f.lower().endswith(".lrc")]

    if not mp3_files and not lrc_files:
        console.print(
            "[dim yellow]⚠️ Tidak ditemukan file MP3 atau LRC mandiri di folder Downloads Anda.[/dim yellow]"
        )
        return

    console.print(
        f"[bold green]✅ Ditemukan {len(mp3_files)} MP3 dan {len(lrc_files)} file LRC di folder Downloads.[/bold green]"
    )

    if not ask_confirm(
        "▶️ Mulai proses perapian (Ganti Nama Otomatis & Pindahkan ke Folder Musik)?",
        default=True,
    ):
        return

    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(lrc_dir, exist_ok=True)

    moved_mp3 = 0
    moved_lrc = 0

    with console.status("[cyan]Merapikan file Anda..."):
        # Match & pindahkan LRC
        for lrc in lrc_files:
            lrc_path = os.path.join(downloads_dir, lrc)
            lrc_name = os.path.splitext(lrc)[0]

            # Cari best match di mp3_files
            mp3_names_stripped = [os.path.splitext(f)[0] for f in mp3_files]
            best_match_stripped = fuzzy_match(lrc_name, mp3_names_stripped, threshold=50)

            if best_match_stripped:
                # Cari index di mp3_files untuk dapatkan nama lengkap
                best_match = next(
                    (f for f in mp3_files if os.path.splitext(f)[0] == best_match_stripped),
                    None,
                )
                if best_match:
                    new_lrc_name = f"{best_match_stripped}.lrc"
                else:
                    new_lrc_name = lrc
            else:
                new_lrc_name = lrc  # pakai nama asli

            target_lrc_path = os.path.join(lrc_dir, new_lrc_name)
            # Timpa jika sudah ada
            if os.path.exists(target_lrc_path):
                os.remove(target_lrc_path)
            try:
                shutil.move(lrc_path, target_lrc_path)
                moved_lrc += 1
                _log.info("LRC moved: %s → %s", lrc, new_lrc_name)
            except Exception as e:
                _log.warning("Gagal pindahkan LRC %s: %s", lrc, e)

        # Pindahkan MP3
        for mp3 in mp3_files:
            mp3_path = os.path.join(downloads_dir, mp3)
            target_mp3_path = os.path.join(music_dir, mp3)
            if os.path.exists(target_mp3_path):
                os.remove(target_mp3_path)
            try:
                shutil.move(mp3_path, target_mp3_path)
                moved_mp3 += 1
                _log.info("MP3 moved: %s", mp3)
            except Exception as e:
                _log.warning("Gagal pindahkan MP3 %s: %s", mp3, e)

    console.print(f"\n[bold green]✨ Proses Perapian Selesai![/bold green]")
    console.print(f"🎵 {moved_mp3} lagu dipindahkan ke: [yellow]{music_dir}[/yellow]")
    console.print(f"🎤 {moved_lrc} lirik dipindahkan ke: [yellow]{lrc_dir}[/yellow]\n")
