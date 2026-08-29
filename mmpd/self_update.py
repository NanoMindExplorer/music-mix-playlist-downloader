"""
`mmpd self-update` — update mmpd secara NON-DESTRUKTIF (Fase C).

Menggantikan one-liner lama:
    rm -rf music-mix-playlist-downloader && git clone ... && pip install ...

yang MENGHAPUS folder repo (beserta config lokal, branch lokal, dan file
yang belum di-commit) setiap kali user ingin update.

Proses baru (aman):
    1. Cari root repo (folder .git) dari lokasi file terpasang
    2. git status --porcelain → tolang update kalau ada perubahan lokal
       (biar pekerjaan user tidak hilang; tampilkan petunjuk stash/commit)
    3. git fetch + git pull --ff-only
    4. pip install -U -e . (atau -U -r requirements.txt dulu)
    5. Cetak versi baru + petunjuk kalau ada file .rej/.bak
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from mmpd import __version__
from mmpd.logger import get_logger

_log = get_logger()


def _find_repo_root() -> Path | None:
    """Cari root repo git dari folder tempat package mmpd terpasang."""
    # Mulai dari lokasi file ini (mode editable install) → naik sampai ketemu .git
    candidate = Path(__file__).resolve().parent
    for _ in range(5):
        if (candidate / ".git").exists():
            return candidate
        if candidate.parent == candidate:
            break
        candidate = candidate.parent
    return None


def _run(cmd: list, cwd: Path | None = None) -> tuple[int, str]:
    """Jalankan command, return (exit_code, output gabungan)."""
    try:
        res = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return res.returncode, (res.stdout or "") + (res.stderr or "")
    except FileNotFoundError:
        return 127, f"command tidak ditemukan: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout setelah 300 detik: {' '.join(cmd)}"


def self_update(pull: bool = True) -> int:
    """
    Update mmpd via git pull + pip install -U -e .

    Returns:
        0 sukses, kode error lain kalau gagal (cocok untuk sys.exit).
    """
    from mmpd.ui import console

    console.print("\n[bold cyan]🔄 mmpd self-update[/bold cyan]")
    console.print(f"[dim]Versi saat ini: {__version__}[/dim]\n")

    repo_root = _find_repo_root()
    if repo_root is None:
        console.print(
            "[bold red]❌ Folder repo git tidak ditemukan.[/bold red]\n"
            "[white]self-update hanya jalan untuk instalasi dari source\n"
            "(git clone + pip install -e .). Untuk instalasi wheel/PyPI, update\n"
            "dengan: pip install -U music-mix-playlist-downloader[/white]\n"
        )
        return 1

    console.print(f"[green]Repo:[/green] {repo_root}")

    # --- 1. Cek working tree bersih ---
    code, out = _run(["git", "status", "--porcelain"], cwd=repo_root)
    if code != 0:
        console.print(f"[bold red]❌ git status gagal:[/bold red] {out.strip()[:200]}")
        return 2
    if out.strip():
        console.print(
            "[bold yellow]⚠️ Ada perubahan lokal yang belum di-commit:[/bold yellow]"
        )
        for line in out.strip().splitlines()[:10]:
            console.print(f"   {line}")
        console.print(
            "\n[white]Update DIBATALKAN supaya perubahan Anda tidak hilang.\n"
            "Simpan dulu pekerjaan Anda:\n"
            "   git add -A && git commit -m 'wip'\n"
            "   # atau: git stash\n"
            "lalu jalankan mmpd self-update lagi.[/white]\n"
        )
        return 3

    if not pull:
        console.print("[dim]--no-pull: skip git pull, langsung reinstall deps.[/dim]")
    else:
        # --- 2. git fetch + pull --ff-only (tidak pernah force/merge destruktif) ---
        console.print("[cyan]➤ git fetch origin...[/cyan]")
        code, out = _run(["git", "fetch", "origin"], cwd=repo_root)
        if code != 0:
            console.print(f"[bold red]❌ git fetch gagal:[/bold red] {out.strip()[:200]}")
            return 4

        console.print("[cyan]➤ git pull --ff-only...[/cyan]")
        code, out = _run(["git", "pull", "--ff-only"], cwd=repo_root)
        if code != 0:
            console.print(f"[bold red]❌ git pull gagal:[/bold red] {out.strip()[:300]}")
            console.print(
                "[dim]Kemungkinan ada commit lokal yang diverge dari origin.\n"
                "Selesaikan manual: git pull --rebase, lalu ulangi self-update --no-pull[/dim]"
            )
            return 5

    # --- 3. Install dependencies baru (kalau requirements berubah) ---
    req = repo_root / "requirements.txt"
    if req.exists():
        console.print("[cyan]➤ pip install -U -r requirements.txt...[/cyan]")
        code, out = _run(
            [sys.executable, "-m", "pip", "install", "-U", "-r", "requirements.txt"],
            cwd=repo_root,
        )
        if code != 0:
            console.print(f"[bold yellow]⚠️ pip install requirements gagal (lanjut):[/bold yellow] {out.strip()[-300:]}")

    # --- 4. Reinstall package (editable) ---
    console.print("[cyan]➤ pip install -U -e . ...[/cyan]")
    code, out = _run([sys.executable, "-m", "pip", "install", "-U", "-e", "."], cwd=repo_root)
    if code != 0:
        console.print(f"[bold red]❌ pip install gagal:[/bold red] {out.strip()[-300:]}")
        return 6

    # --- 5. Selesai: tampilkan versi baru ---
    try:
        import importlib
        import mmpd
        importlib.reload(mmpd)
        new_version = mmpd.__version__
    except Exception:
        new_version = __version__

    console.print(f"\n[bold green]✅ Update selesai → mmpd {new_version}[/bold green]")
    console.print("[dim]Jalankan 'mmpd doctor' untuk memastikan semua dependency sehat.[/dim]\n")
    return 0
