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

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class LyricLine:
    """
    Satu baris lirik ter-struktur (Fase A / P2).

    Model tunggal untuk pipeline lirik — menggantikan manipulasi string rawak
    terhadap baris LRC mentah di banyak tempat. Semua tahap pipeline
    (fetch → translate → transliterate → format) memakai model ini.

    Field:
        ts:       timestamp dalam DETIK (mis. 61.5 untuk [01:01.50]); None =
                  baris tanpa timestamp (metadata [ti:..] dsb.)
        original: teks aksara ASLI (Hanzi/Kana/Hangul/Thai) — sumber terjemahan
        latin:    teks hasil transliterasi (pinyin/romaji/jyutping); None kalau
                  belum di-transliterasi
        id_text:  terjemahan Bahasa Indonesia (None kalau belum diterjemahkan)
    """

    ts: Optional[float]
    original: str = ""
    latin: Optional[str] = None
    id_text: Optional[str] = None

    @property
    def display(self) -> str:
        """Teks tampilan: versi latin kalau ada, kalau tidak aksara asli."""
        return self.latin if self.latin else self.original

    @property
    def has_translation(self) -> bool:
        return bool(self.id_text and self.id_text.strip())

    def to_lrc_line(self) -> str:
        """Render kembali ke satu baris LRC '[mm:ss.cc]teks'."""
        if self.ts is None:
            return self.original
        mins = int(self.ts // 60)
        secs = self.ts % 60
        return f"[{mins:02d}:{secs:05.2f}]{self.display}"


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
        """Query pencarian bersih — didelegasikan ke normalize_track_query (P0/Fase L).

        Dulu method ini punya regex sendiri yang LEBIH SEMPIT daripada
        mmpd.utils.matching.clean_search_query (tanpa OpenCC, tanpa promo
        multi-bahasa lengkap) → dua jalur kode menghasilkan query berbeda
        untuk lagu yang sama. Sekarang satu implementasi tunggal.
        """
        from mmpd.utils.matching import normalize_track_query
        return normalize_track_query(self.title, self.artist)


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
