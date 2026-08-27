"""
Type definitions untuk lyrics providers.

Mendefinisikan:
- `LyricsProvider` Protocol: interface yang harus diimplementasi semua provider
- `LyricsResult` dataclass: hasil pencarian lirik dengan metadata
- `TrackInfo` dataclass: info track untuk pencarian (title, artist, duration, isrc)

Tujuan:
- Memungkinkan A/B testing antar provider (LRCLIB vs syncedlyrics vs Musixmatch)
- Memudahkan penambahan provider baru tanpa modif caller code
- Enable fallback chain (coba provider A, kalau gagal coba B, dst.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class TrackInfo:
    """
    Info minimal track untuk pencarian lirik.

    Field:
        title:    Judul lagu (wajib)
        artist:   Nama artist (opsional, meningkatkan akurasi)
        album:    Nama album (opsional, untuk disambiguation)
        duration: Durasi lagu dalam detik (opsional, untuk sync verification)
        isrc:     International Standard Recording Code (opsional, paling akurat)
                  Format: CC-XXX-YY-NNNNN (mis. 'USUM71703861')
    """

    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    duration: Optional[float] = None  # detik
    isrc: Optional[str] = None

    def search_query(self) -> str:
        """Build search query string dari info yang tersedia."""
        parts = [self.title]
        if self.artist:
            parts.append(self.artist)
        return " ".join(parts)

    def clean_search_query(self) -> str:
        """Search query setelah strip bracket/parenthetical (mis. 'Song (Official Video)' → 'Song')."""
        import re
        q = self.search_query()
        # Hapus [bracket], (parenthetical), 【japanese bracket】
        q = re.sub(r"\[.*?\]|\(.*?\)|【.*?】", "", q).strip()
        # Hapus kata kunci promo
        q = re.sub(r"(?i)\b(official|music video|mv|lyric|video|audio|cover)\b", "", q).strip()
        # Collapse multiple spaces
        q = re.sub(r"\s+", " ", q).strip()
        return q


@dataclass(frozen=True)
class LyricsResult:
    """
    Hasil pencarian lirik dari satu provider.

    Field:
        synced_lyrics: Lirik format LRC dengan timestamp (mis. '[00:01.23]Hello world')
                       Empty string jika hanya plain lyrics tersedia.
        plain_lyrics:  Lirik tanpa timestamp (fallback kalau synced tidak ada).
        provider:      Nama provider yang mengembalikan hasil (untuk logging).
        track_name:    Judul track yang ditemukan oleh provider (untuk verifikasi match).
        artist_name:   Artist track yang ditemukan.
        duration_ms:   Durasi track dari provider (untuk sync verification).
    """

    synced_lyrics: str
    plain_lyrics: Optional[str] = None
    provider: str = "unknown"
    track_name: Optional[str] = None
    artist_name: Optional[str] = None
    duration_ms: Optional[int] = None

    @property
    def has_synced(self) -> bool:
        """True jika punya synced lyrics (LRC dengan timestamp)."""
        return bool(self.synced_lyrics and self.synced_lyrics.strip())

    @property
    def best_lyrics(self) -> str:
        """Return synced_lyrics jika ada, fallback ke plain_lyrics."""
        if self.has_synced:
            return self.synced_lyrics
        return self.plain_lyrics or ""


@runtime_checkable
class LyricsProvider(Protocol):
    """
    Protocol yang harus diimplementasi semua lyrics provider.

    Implementasi:
    - LrclibProvider        — pakai LRCLIB API (https://lrclib.net)
    - SyncedLyricsProvider  — wrapper syncedlyrics library (current default)
    - YoutubeCCProvider     — pakai YouTube closed captions (untuk cover songs)

    Contract:
        - search(track: TrackInfo) -> Optional[LyricsResult]
        - name: str  (untuk logging)
        - priority: int  (urutan dalam fallback chain, lower = higher priority)
    """

    name: str
    priority: int  # 0 = highest priority

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        """
        Cari lirik untuk track. Return None jika tidak ditemukan.

        Implementasi HARUS:
        - Tidak raise exception untuk "tidak ditemukan" (return None)
        - Hanya raise exception untuk error sistemik (network down, auth fail)
        - Handle timeout sendiri (jangan biarkan caller blocking terlalu lama)
        - Return LyricsResult dengan `provider` field diisi nama provider
        """
        ...
