"""
Mode 3: Auto-Organizer (Pengatur Otomatis).

Skenario: User download lirik (.lrc) manual di internet, taruh di folder
Downloads secara berantakan. Mode ini akan:
    1. Cari file .lrc dan .mp3/.flac di folder target
    2. Match nama .lrc dengan file audio (rapidfuzz, case-insensitive)
    3. Rename .lrc agar sama persis dengan file audio
    4. Pindahkan audio ke folder Music, .lrc ke folder Musiclrc (Huawei style)

Fase A/P1:
    - Scan REKURSIF (dulu hanya root folder — subfolder terlewat)
    - DRY-RUN: preview rencana rename/move tanpa mengeksekusi apa pun
    - run_organizer_noninteractive() untuk CLI `mmpd organize`
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from mmpd.config import get_config
from mmpd.logger import get_logger
from mmpd.ui import ask_confirm, console
from mmpd.utils.matching import fuzzy_match

_log = get_logger()

_AUDIO_EXTS = (".mp3", ".flac", ".m4a", ".wav")


def _scan_files(folder: str, recursive: bool) -> Tuple[List[str], List[str]]:
    """Scan folder → (list path audio, list path lrc)."""
    audio_files: List[str] = []
    lrc_files: List[str] = []
    if recursive:
        for root, _, files in os.walk(folder):
            for f in files:
                p = os.path.join(root, f)
                if f.lower().endswith(_AUDIO_EXTS):
                    audio_files.append(p)
                elif f.lower().endswith(".lrc") and not f.lower().endswith(".id.lrc"):
                    lrc_files.append(p)
    else:
        for f in os.listdir(folder):
            p = os.path.join(folder, f)
            if not os.path.isfile(p):
                continue
            if f.lower().endswith(_AUDIO_EXTS):
                audio_files.append(p)
            elif f.lower().endswith(".lrc") and not f.lower().endswith(".id.lrc"):
                lrc_files.append(p)
    return sorted(audio_files), sorted(lrc_files)


def _plan_moves(
    lrc_files: List[str],
    audio_files: List[str],
    lrc_dir: str,
    music_dir: str,
) -> List[Tuple[str, str, str]]:
    """Susun rencana perpindahan. Return list (src, dst, jenis_aksi)."""
    plans: List[Tuple[str, str, str]] = []
    audio_names = [os.path.splitext(os.path.basename(a))[0] for a in audio_files]

    for lrc_path in lrc_files:
        lrc_name = os.path.splitext(os.path.basename(lrc_path))[0]
        best_match = fuzzy_match(lrc_name, audio_names, threshold=50)

        if best_match:
            new_name = f"{best_match}.lrc"
        else:
            new_name = os.path.basename(lrc_path)  # pakai nama asli

        dst = os.path.join(lrc_dir, new_name)
        plans.append((lrc_path, dst, f"lrc→{new_name}"))

    for audio_path in audio_files:
        dst = os.path.join(music_dir, os.path.basename(audio_path))
        plans.append((audio_path, dst, f"audio→{os.path.basename(audio_path)}"))

    return plans


def _execute_plans(plans: List[Tuple[str, str, str]]) -> Tuple[int, int]:
    """Jalankan rencana move. Return (moved_audio, moved_lrc)."""
    moved_audio = 0
    moved_lrc = 0
    for src, dst, kind in plans:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst):
                os.remove(dst)  # timpa versi lama di tujuan
            shutil.move(src, dst)
            if kind.startswith("audio"):
                moved_audio += 1
            else:
                moved_lrc += 1
            _log.info("Organizer move: %s → %s", src, dst)
        except Exception as e:
            _log.warning("Gagal pindahkan %s: %s", src, e)
    return moved_audio, moved_lrc


def run_organizer(
    folder: Optional[str] = None,
    recursive: bool = True,
    dry_run: bool = False,
    confirm: bool = True,
) -> int:
    """
    Jalankan Mode 3: Auto-Organizer (interaktif, dengan konfirmasi).

    Args:
        folder:    folder sumber (default: Downloads; prompt kalau None)
        recursive: scan subfolder juga (default True — Fase A)
        dry_run:   hanya tampilkan rencana, JANGAN pindahkan apa pun

    Returns:
        0 sukses / 1 folder tidak valid / 2 tidak ada file.
    """
    console.print("\n[bold cyan]📁 Mode 3: Pengatur Otomatis (Auto-Organizer)[/bold cyan]")
    console.print(
        "[white]Sistem akan mencari lagu & lirik yang Anda unduh secara manual, "
        "lalu menyamakan namanya dan memindahkannya ke folder Music "
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

    target_folder = folder or downloads_dir
    if folder is None:
        # Prompt folder hanya di TTY; di non-interaktif pakai default.
        try:
            from mmpd.ui import ask_text
            answer = ask_text("Masukkan folder yang ingin dirapikan:", default=downloads_dir)
            if answer:
                target_folder = answer
        except (EOFError, Exception):
            pass

    if not os.path.exists(target_folder):
        console.print(f"[bold red]❌ Folder tidak ditemukan: {target_folder}[/bold red]")
        return 1

    audio_files, lrc_files = _scan_files(target_folder, recursive)
    if not audio_files and not lrc_files:
        console.print(
            "[dim yellow]⚠️ Tidak ditemukan file audio/LRC di folder tersebut.[/dim yellow]"
        )
        return 2

    scope = "rekursif (termasuk subfolder)" if recursive else "hanya root folder"
    console.print(
        f"[bold green]✅ Ditemukan {len(audio_files)} audio dan {len(lrc_files)} file LRC ({scope}).[/bold green]"
    )

    plans = _plan_moves(lrc_files, audio_files, lrc_dir, music_dir)

    # Preview rencana (dry-run style) — Fase A
    console.print(f"\n[bold]📋 Rencana perapian ({len(plans)} aksi):[/bold]")
    for src, _dst, kind in plans[:20]:
        console.print(f"  [cyan]{kind}[/cyan] [dim]{os.path.basename(src)}[/dim]")
    if len(plans) > 20:
        console.print(f"  [dim]... dan {len(plans) - 20} aksi lainnya[/dim]")
    console.print(f"\n[bold]🎧 Musik →[/bold] [yellow]{music_dir}[/yellow]")
    console.print(f"[bold]🎤 Lirik  →[/bold] [yellow]{lrc_dir}[/yellow]\n")

    if dry_run:
        console.print("[bold yellow]🔍 DRY-RUN: tidak ada file yang dipindahkan.[/bold yellow]")
        return 0

    # CLI non-interaktif (confirm=False) skip prompt.
    # Interaktif: EOF/CI → auto-proceed dengan default True.
    if confirm:
        try:
            confirmed = ask_confirm(
                "▶️ Mulai proses perapian (Ganti Nama Otomatis & Pindahkan ke Folder Musik)?",
                default=True,
            )
        except (EOFError, Exception):
            confirmed = True
        if confirmed is False:
            return 0

    os.makedirs(music_dir, exist_ok=True)
    os.makedirs(lrc_dir, exist_ok=True)

    with console.status("[cyan]Merapikan file Anda..."):
        moved_audio, moved_lrc = _execute_plans(plans)

    console.print("\n[bold green]✨ Proses Perapian Selesai![/bold green]")
    console.print(f"🎵 {moved_audio} lagu dipindahkan ke: [yellow]{music_dir}[/yellow]")
    console.print(f"🎤 {moved_lrc} lirik dipindahkan ke: [yellow]{lrc_dir}[/yellow]\n")
    return 0


def run_organizer_noninteractive(
    folder: str,
    recursive: bool = True,
    dry_run: bool = False,
) -> int:
    """Alias non-interaktif untuk CLI `mmpd organize` (tanpa konfirmasi)."""
    return run_organizer(folder=folder, recursive=recursive, dry_run=dry_run, confirm=False)
