"""mmpd.utils — subpackage berisi utility functions terpisah per concern.

Modul-modul di sini bersifat stateless dan tidak bergantung pada UI/console.
Tujuan utamanya agar mudah di-unit-test.

Submodul:
    ffmpeg    - FFmpeg wrapper (cover art injection, audio conversion)
    fs        - Filesystem helpers (atomic write, path sanitize, file ops)
    matching  - Title matching (rapidfuzz wrapper, query cleaning)
"""

from __future__ import annotations

__all__: list[str] = []
