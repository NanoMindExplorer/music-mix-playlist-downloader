"""mmpd.modes — subpackage untuk mode-mode operasi CLI.

Setiap modul mewakili satu mode di menu utama:
    retrofit    — Mode 2 (Perbaiki file lama: cari & suntik lirik/cover)
    organizer   — Mode 3 (Pengatur otomatis LRC/MP3 unduhan manual)
    download    — Mode 1, 4, 5 (YouTube / Spotify / SoundCloud download)

Tujuan extraction: agar logic setiap mode terpisah, mudah di-test, dan
tidak bloat downloader.py (Fase 2.2 goal: downloader.py jadi thin entry).
"""

from __future__ import annotations

__all__: list[str] = []
