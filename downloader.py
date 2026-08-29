"""
music-mix-playlist-downloader — Thin entry point.

Fase 2.2: seluruh logic sudah di-extract ke package `mmpd/`. File ini
sekarang hanya berisi:
  1. Import dependencies yang diperlukan (untuk backward compat)
  2. Re-export public API yang dipakai caller lama
  3. Entry point `__main__` dan `main()`

Backward compatible:
    python downloader.py            # tetap jalan
    mmpd                            # tetap jalan (entry point)

Modular:
    from mmpd.modes.download import run_cli
    from mmpd.lyrics import fetch_synced_lyrics, process_transliteration
    from mmpd.modes.retrofit import run_retrofit
    from mmpd.modes.organizer import run_organizer
"""

from __future__ import annotations

import sys

# ============================================================================
# Import dependencies yang diperlukan untuk backward compatibility.
# Beberapa caller lama mungkin masih import langsung dari `downloader`.
# ============================================================================

# yt-dlp import akan raise ModuleNotFoundError kalau belum terinstal.
# Tampilkan pesan error yang user-friendly.
try:
    import yt_dlp
except ModuleNotFoundError:
    print("\n❌ Modul 'yt_dlp' belum terinstal!")
    print("Silakan jalankan perintah berikut untuk menginstal pembaruan:")
    print("pip install -U -r requirements.txt\n")
    sys.exit(1)

# syncedlyrics dengan timeout patch (sama seperti Fase 1)
try:
    import syncedlyrics
    from syncedlyrics.providers.base import TimeoutSession

    def custom_request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (10, 30))  # Connect 10s, Read 30s
        return super(TimeoutSession, self).request(method, url, **kwargs)

    TimeoutSession.request = custom_request
except ModuleNotFoundError:
    print("\n❌ Modul 'syncedlyrics' belum terinstal!")
    print("Silakan jalankan perintah berikut untuk menginstal pembaruan:")
    print("pip install -U -r requirements.txt\n")
    sys.exit(1)


# ============================================================================
# Re-export public API dari mmpd/ package untuk backward compatibility.
# Caller lama yang `from downloader import run_cli` tetap berfungsi.
# ============================================================================

from mmpd.config import get_default_path  # backward-compat: masih dipakai beberapa caller
from mmpd.ui import console, custom_theme  # backward-compat: dipakai test/script lama
from mmpd.ytdlp import YTDLPLogger

# Import lazy agar `python -m mmpd --version` cepat tanpa import yt_dlp dkk.
def run_cli() -> None:
    """Jalankan CLI utama (mode interaktif). Backward compat entry point."""
    from mmpd.modes.download import run_cli as _run_cli
    _run_cli()


def run_retrofit() -> None:
    """Mode 2: Retrofit Engine. Backward compat entry point."""
    from mmpd.modes.retrofit import run_retrofit as _run_retrofit
    _run_retrofit()


def run_organizer() -> None:
    """Mode 3: Auto-Organizer. Backward compat entry point."""
    from mmpd.modes.organizer import run_organizer as _run_organizer
    _run_organizer()


# Re-export lyrics functions (dipakai oleh test/script lama)
from mmpd.lyrics import (
    fetch_synced_lyrics,
    process_translation,
    process_transliteration,
    sync_huawei_lrc,
)

# Re-export utils (dipakai oleh test/script lama)
from mmpd.utils.fs import atomic_write_text as _atomic_write_text  # backward-compat alias


# ============================================================================
# Entry points
# ============================================================================

def main() -> None:
    """
    Entry point untuk `mmpd` console script (setelah `pip install .`).

    Fase C: seluruh dispatch subcommand sekarang ada di mmpd.cli (argparse).
    File ini tetap sebagai thin wrapper untuk backward compatibility.

    Mendukung subcommand:
        mmpd                          # mode interaktif (sama dengan `python downloader.py`)
        mmpd download|retrofit|lyrics # mode non-interaktif (Fase C)
        mmpd cache|config             # utilitas
        mmpd doctor                   # jalankan diagnostik
        mmpd self-update              # update non-destruktif (Fase C)
        mmpd --version                # cetak versi
    """
    try:
        from mmpd.cli import main as cli_main
        sys.exit(cli_main())
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Aplikasi dihentikan secara paksa (Ctrl+C).[/bold red]")
        sys.exit(0)


if __name__ == "__main__":
    main()
