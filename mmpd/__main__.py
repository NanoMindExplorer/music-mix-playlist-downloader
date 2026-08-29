"""
Entry point untuk `python -m mmpd`.

Cara pakai:
    python -m mmpd            # jalankan CLI utama (sama dengan `python downloader.py`)
    python -m mmpd doctor      # jalankan diagnostik
    python -m mmpd --version   # cetak versi
"""

from __future__ import annotations

import sys


def main() -> int:
    """Entry point untuk `python -m mmpd`."""
    args = sys.argv[1:]

    # Subcommand: doctor
    if args and args[0] == "doctor":
        from mmpd.doctor import run_doctor
        return run_doctor()

    # Subcommand: --version / -V
    if args and args[0] in ("--version", "-V"):
        from mmpd import __version__
        print(f"mmpd {__version__}")
        return 0

    # Default: jalankan CLI utama (downloader.run_cli)
    # Import lazy agar `python -m mmpd --version` cepat tanpa import yt_dlp dkk.
    try:
        from downloader import run_cli
        from mmpd.logger import setup_logging
        import logging
        setup_logging(level=logging.WARNING, enable_console=True)
        run_cli()
        return 0
    except KeyboardInterrupt:
        print("\n\nAplikasi dihentikan secara paksa (Ctrl+C).")
        return 0
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
