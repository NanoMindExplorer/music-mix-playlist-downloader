"""
Entry point untuk `python -m mmpd`.

Fase C: seluruh dispatch subcommand (download/retrofit/lyrics/cache/config/
doctor/self-update) sekarang ada di mmpd.cli (argparse).

Cara pakai:
    python -m mmpd                     # menu interaktif (sama dengan `python downloader.py`)
    python -m mmpd download URL --format mp3
    python -m mmpd retrofit --dir DIR --lyrics-only --translate
    python -m mmpd doctor              # jalankan diagnostik
    python -m mmpd self-update         # update non-destruktif
    python -m mmpd --version           # cetak versi
"""

from __future__ import annotations

import sys


def main() -> int:
    """Entry point untuk `python -m mmpd`."""
    from mmpd.cli import main as cli_main

    try:
        return cli_main()
    except KeyboardInterrupt:
        print("\n\nAplikasi dihentikan secara paksa (Ctrl+C).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
