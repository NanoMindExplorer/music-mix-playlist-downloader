"""
Music Mix & Playlist Downloader Pro (AI Edition)
=================================================

Package `mmpd` berisi modul-modul infrastruktur yang dipakai oleh CLI utama
(`downloader.py`). Struktur package memungkinkan:

- Entry point `mmpd` (via `pip install .`)
- `python -m mmpd` sebagai alternatif
- Backward compatible: `python downloader.py` tetap berfungsi

Submodul:
    config           - Path & environment detection terpusat
    logger           - Structured logging dengan file rotation
    types            - Type definitions (Protocol, TypedDict, dataclass)
    lyrics_providers - Abstraksi multi-provider lirik (LRCLIB + syncedlyrics)
    doctor           - `mmpd doctor` command untuk diagnostics
"""

from __future__ import annotations

__version__ = "3.1.0"
__author__ = "NanoMindExplorer"
__license__ = "MIT"

__all__: list[str] = [
    "__version__",
    "__author__",
    "__license__",
]
