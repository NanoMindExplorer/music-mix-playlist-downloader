"""
`mmpd doctor` — Diagnostics command untuk troubleshooting.

Cek:
- Dependency sistem (ffmpeg, git)
- Dependency Python (yt-dlp, rich, syncedlyrics, rapidfuzz, requests, dll)
- Network connectivity (LRCLIB, iTunes, Spotify)
- Storage permission (Termux)
- Path konfigurasi (log, cache, output)

Usage:
    python -m mmpd doctor       # via module
    mmpd doctor                  # via entry point (setelah pip install)
    python mmpd/doctor.py        # direct script
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from mmpd import __version__
from mmpd.config import get_config


# ANSI color codes (lightweight, no external dep)
class Color:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def _ok(msg: str) -> str:
    return f"{Color.GREEN}[OK]{Color.RESET}     {msg}"


def _fail(msg: str) -> str:
    return f"{Color.RED}[FAIL]{Color.RESET}   {msg}"


def _warn(msg: str) -> str:
    return f"{Color.YELLOW}[WARN]{Color.RESET}   {msg}"


def _info(msg: str) -> str:
    return f"{Color.CYAN}[INFO]{Color.RESET}   {msg}"


def _section(title: str) -> str:
    return f"\n{Color.BOLD}=== {title} ==={Color.RESET}"


def _check_binary(name: str, min_version: str = "") -> Tuple[bool, str]:
    """Cek apakah binary ada di PATH, plus versi kalau bisa."""
    path = shutil.which(name)
    if path is None:
        return False, "tidak ditemukan di PATH"
    if min_version:
        try:
            res = subprocess.run(
                [name, "-version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            first_line = (res.stdout or res.stderr).split("\n")[0]
            return True, f"{path} — {first_line[:80]}"
        except Exception:
            return True, f"{path}"
    return True, path


def _check_module(name: str) -> Tuple[bool, str]:
    """Cek apakah Python module bisa di-import, plus versi."""
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        return True, f"v{version}"
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _check_network(host: str, port: int = 443, timeout: float = 5.0) -> Tuple[bool, str]:
    """Cek TCP connectivity ke host:port."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.create_connection((host, port), timeout=timeout) as _:
            return True, f"connected to {host}:{port}"
    except Exception as e:
        return False, f"{host}:{port} — {e}"


def _check_writable(path: Path) -> Tuple[bool, str]:
    """Cek apakah path bisa ditulis."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".doctor_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        return True, str(path)
    except Exception as e:
        return False, f"{path} — {e}"


def run_doctor() -> int:
    """
    Jalankan semua diagnostic checks. Return exit code:
        0 = semua OK
        1 = ada failure (FAIL)
        2 = hanya warning (WARN), no FAIL
    """
    try:
        from mmpd.config_loader import load_config
        load_config()
    except Exception:
        pass

    print(f"\n{Color.BOLD}🎵 Music Mix Playlist Downloader Pro — Doctor v{__version__}{Color.RESET}")
    print(f"{Color.DIM}Python {sys.version.split()[0]} on {platform.system()} {platform.machine()}{Color.RESET}")
    print(f"{Color.DIM}PID: {os.getpid()}{Color.RESET}")

    fails: List[str] = []
    warns: List[str] = []

    # === 1. System Binaries ===
    print(_section("1. System Binaries"))

    for binary, min_ver in [("ffmpeg", "any"), ("git", "any")]:
        ok, info = _check_binary(binary, min_ver)
        if ok:
            print(_ok(f"{binary}: {info}"))
        else:
            print(_fail(f"{binary}: {info}"))
            fails.append(f"{binary} missing")

    # === 2. Python Modules ===
    print(_section("2. Python Modules"))

    required_modules = [
        "yt_dlp",
        "rich",
        "mutagen",
        "questionary",
        "syncedlyrics",
        "pykakasi",
        "pypinyin",
        "langdetect",
        "korean_romanizer",
        "anyascii",
        "deep_translator",
        "rapidfuzz",
        "requests",
        # Fase 2.3: spotipy sekarang required (untuk ISRC matching akurasi 99%+)
        "spotipy",
    ]

    for mod in required_modules:
        ok, info = _check_module(mod)
        if ok:
            print(_ok(f"{mod:20s} {info}"))
        else:
            print(_fail(f"{mod:20s} {info}"))
            fails.append(f"{mod} not installed")

    # Optional modules (tidak ada lagi — spotipy sudah required di Fase 2.3)

    # === 2b. Fase 2.3: Spotify API credentials check ===
    print(_section("2b. Spotify API Credentials (untuk ISRC matching)"))

    spotify_id = os.environ.get("SPOTIPY_CLIENT_ID", "")
    spotify_secret = os.environ.get("SPOTIPY_CLIENT_SECRET", "")

    if spotify_id and spotify_secret:
        print(_ok(f"SPOTIPY_CLIENT_ID     set ({len(spotify_id)} chars, masked: {spotify_id[:4]}***{spotify_id[-2:]})"))
        print(_ok(f"SPOTIPY_CLIENT_SECRET set ({len(spotify_secret)} chars)"))
        print(_info("Spotify ISRC matching AKTIF (akurasi YouTube matching 99%+)"))
    else:
        # Cek apakah spotipy terinstal
        spotipy_ok, _ = _check_module("spotipy")
        if spotipy_ok:
            print(_warn("spotipy terinstal tapi credentials SPOTIPY_CLIENT_ID/SECRET belum diset"))
            print(_info("   Tanpa credentials, ISRC matching tidak jalan (fallback ke fuzzy matching)"))
            print(_info("   Setup:"))
            print(_info("     1. Buka https://developer.spotify.com/dashboard"))
            print(_info("     2. Create app → dapatkan Client ID + Client Secret"))
            print(_info("     3. Set environment variables:"))
            print(_info('        export SPOTIPY_CLIENT_ID="your_client_id"'))
            print(_info('        export SPOTIPY_CLIENT_SECRET="your_client_secret"'))
            warns.append("Spotify credentials not set (ISRC matching disabled)")
        else:
            print(_info("Spotipy tidak terinstal — Spotify parser pakai legacy scraping"))

    # === 3. Network Connectivity ===
    print(_section("3. Network Connectivity"))

    endpoints = [
        ("lrclib.net", 443, "LRCLIB lyrics API"),
        ("itunes.apple.com", 443, "iTunes search API (Formula Cerdas)"),
        ("api.spotify.com", 443, "Spotify API"),
        ("open.spotify.com", 443, "Spotify embed scraping"),
        ("www.youtube.com", 443, "YouTube (yt-dlp source)"),
        ("soundcloud.com", 443, "SoundCloud (yt-dlp source)"),
        ("music.163.com", 443, "NetEase API (syncedlyrics)"),
        ("www.megalobiz.com", 443, "Megalobiz (syncedlyrics)"),
        ("translate.google.com", 443, "Google Translate API"),
        ("api.mymemory.translated.net", 443, "MyMemory Translate API"),
    ]

    for host, port, desc in endpoints:
        ok, info = _check_network(host, port)
        if ok:
            print(_ok(f"{desc:35s} {info}"))
        else:
            print(_warn(f"{desc:35s} {info}"))
            warns.append(f"network {host} unreachable")

    # === 4. Storage & Permissions ===
    print(_section("4. Storage & Permissions"))

    config = get_config()
    paths_to_check = [
        ("Output dir", config.output_dir),
        ("Log dir", config.log_dir),
        ("Cache dir", config.cache_dir),
    ]

    for name, path in paths_to_check:
        ok, info = _check_writable(path)
        if ok:
            print(_ok(f"{name:15s} {info}"))
        else:
            print(_fail(f"{name:15s} {info}"))
            fails.append(f"{name} not writable")

    # Termux storage permission
    if config.is_termux:
        storage_path = Path.home() / "storage"
        if storage_path.exists() and storage_path.is_symlink():
            print(_ok(f"Termux storage: {storage_path} (symlink OK)"))
        else:
            print(_warn("Termux storage belum di-setup"))
            print(_info("   Jalankan: termux-setup-storage"))
            warns.append("termux-setup-storage belum dijalankan")

    # === 5. Configuration ===
    print(_section("5. Configuration"))

    print(_info(f"Environment: {'Termux' if config.is_termux else 'Windows' if config.is_windows else 'Linux/macOS'}"))
    print(_info(f"Home dir:    {config.home_dir}"))
    print(_info(f"Output dir:  {config.output_dir}"))
    print(_info(f"Log file:    {config.log_dir / 'mmpd.log'}"))
    print(_info(f"Config file: {config.config_file}"))

    if config.config_file.exists():
        print(_ok(f"Config file ditemukan: {config.config_file}"))
    else:
        print(_info("Config file belum ada (akan dibuat saat user set preferences)"))

    # === Summary ===
    print(_section("Summary"))
    if fails:
        print(_fail(f"{len(fails)} failure(s):"))
        for f in fails:
            print(f"   - {f}")
        print(_info("Fix failures di atas sebelum menggunakan mmpd."))
        return 1
    elif warns:
        print(_warn(f"{len(warns)} warning(s) (non-blocking):"))
        for w in warns:
            print(f"   - {w}")
        print(_info("Aplikasi tetap bisa jalan, tapi beberapa fitur mungkin tidak optimal."))
        return 2
    else:
        print(f"\n{Color.BOLD}{Color.GREEN}✅ Semua check PASSED! Aplikasi siap digunakan.{Color.RESET}")
        print(_info("Cara pakai:"))
        print(_info("   mmpd                       # menu interaktif"))
        print(_info("   mmpd download URL --format mp3 --translate"))
        print(_info("   mmpd doctor                # re-run diagnostics ini"))
        print(_info("   mmpd completion bash >> ~/.bashrc"))
        return 0


if __name__ == "__main__":
    sys.exit(run_doctor())
