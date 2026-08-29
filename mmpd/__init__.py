"""
Music Mix & Playlist Downloader (mmpd)
======================================

Package `mmpd` berisi seluruh modul infrastruktur CLI:

- Entry point `mmpd` (via `pip install .`)
- `python -m mmpd` sebagai alternatif
- Backward compatible: `python downloader.py` tetap berfungsi

Submodul:
    config           - Path & environment detection terpusat
    logger           - Structured logging dengan file rotation
    types            - Type definitions (Protocol, TypedDict, dataclass)
    lyrics_providers - Abstraksi multi-provider lirik (fallback chain)
    cache            - SQLite cache (translation + lyrics, TTL)
    doctor           - `mmpd doctor` command untuk diagnostics

CATATAN VERSI (P0/Fase H): `mmpd.__version__` di file ini adalah SATU-SATUNYA
sumber versi. pyproject.toml membacanya via setuptools dynamic attr; UI banner
dan `mmpd --version` membacanya dari sini. Jangan hardcode versi di tempat lain.
"""

from __future__ import annotations

__version__ = "4.1.0"
__author__ = "NanoMindExplorer"
__license__ = "MIT"

__all__: list[str] = [
    "__version__",
    "__author__",
    "__license__",
]
