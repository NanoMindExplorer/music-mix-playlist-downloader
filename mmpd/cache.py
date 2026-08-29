"""
Persistent cache untuk translation + lyrics, menghindari re-fetch/re-translate
yang sama berulang kali.

Pakai SQLite (built-in Python, no external dep) — ringan, atomic, thread-safe.

Cache keys:
    - Translation: SHA256(source_text + source_lang + target_lang) → translated_text
    - Lyrics: SHA256(track_title + artist + isrc) → synced_lyrics

Cache invalidation:
    - Translation: tidak pernah expire (translation jarang berubah)
    - Lyrics: optional TTL (default 30 hari) — lirik bisa berubah kalau
      provider update database

Storage location (sesuai Fase 2.1 config):
    Linux/macOS: ~/.local/share/mmpd/cache/cache.db
    Termux:      $PREFIX/var/cache/mmpd/cache.db
    Windows:     %LOCALAPPDATA%/mmpd/cache/cache.db
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

from mmpd.config import get_config
from mmpd.logger import get_logger

_log = get_logger()

# Constants
_DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
_DB_FILENAME = "cache.db"

# Singleton
_DB_PATH: Optional[Path] = None
_LOCK = threading.Lock()


def _get_db_path() -> Path:
    """Dapatkan path database cache (singleton)."""
    global _DB_PATH
    if _DB_PATH is None:
        config = get_config()
        try:
            config.ensure_dirs()
            _DB_PATH = config.cache_dir / _DB_FILENAME
        except Exception:
            # Fallback kalau config.ensure_dirs() gagal (mis. permission)
            _DB_PATH = Path("/tmp") / "mmpd_cache.db" if Path("/tmp").exists() else Path.home() / ".mmpd_cache.db"
    return _DB_PATH


def _init_db(conn: sqlite3.Connection) -> None:
    """Buat tabel cache kalau belum ada."""
    cursor = conn.cursor()
    # Translation cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS translation_cache (
            cache_key TEXT PRIMARY KEY,
            source_text TEXT NOT NULL,
            source_lang TEXT,
            target_lang TEXT NOT NULL,
            translated_text TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            provider TEXT
        )
    """)
    # Lyrics cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lyrics_cache (
            cache_key TEXT PRIMARY KEY,
            track_title TEXT NOT NULL,
            artist TEXT,
            isrc TEXT,
            synced_lyrics TEXT,
            plain_lyrics TEXT,
            provider TEXT,
            created_at INTEGER NOT NULL,
            expires_at INTEGER
        )
    """)
    # Index untuk lookup by isrc (lebih cepat)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lyrics_isrc ON lyrics_cache(isrc)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_lyrics_title ON lyrics_cache(track_title)")
    conn.commit()


_DB_INITIALIZED = False
_GLOBAL_CONN = None

def _get_connection() -> sqlite3.Connection:
    """Buka koneksi SQLite + init tabel (sekali per process)."""
    global _DB_INITIALIZED, _GLOBAL_CONN
    
    with _LOCK:
        if _GLOBAL_CONN is not None:
            return _GLOBAL_CONN
            
        db_path = _get_db_path()
        conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
        _init_db(conn)
        _DB_INITIALIZED = True
        _GLOBAL_CONN = conn
            
    return conn


def _hash_key(*parts: str) -> str:
    """Buat SHA256 hash dari gabungan string parts."""
    combined = "|".join(str(p) for p in parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


# ============================================================================
# Translation cache
# ============================================================================

def get_translation_cache(
    source_text: str,
    source_lang: str,
    target_lang: str,
) -> Optional[str]:
    """
    Cek translation cache. Return translated_text kalau ada, None kalau miss.

    Args:
        source_text: Text yang akan diterjemahkan
        source_lang: Kode bahasa source (mis. 'en', 'auto')
        target_lang: Kode bahasa target (mis. 'id')

    Returns:
        Translated text kalau cache hit, None kalau miss.
    """
    cache_key = _hash_key(source_text, source_lang, target_lang)
    try:
        with _LOCK, _get_connection() as conn:
            cursor = conn.execute(
                "SELECT translated_text FROM translation_cache WHERE cache_key = ?",
                (cache_key,),
            )
            row = cursor.fetchone()
            if row:
                _log.debug("Translation cache HIT: %s...", source_text[:30])
                return row[0]
        _log.debug("Translation cache MISS: %s...", source_text[:30])
    except Exception as e:
        _log.warning("Translation cache read error: %s", e)
    return None


def set_translation_cache(
    source_text: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
    provider: Optional[str] = None,
) -> None:
    """
    Simpan translation ke cache.

    Translation cache TIDAK pernah expire — translation jarang berubah
    (Google Translate output stabil).
    """
    cache_key = _hash_key(source_text, source_lang, target_lang)
    try:
        with _LOCK, _get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO translation_cache
                   (cache_key, source_text, source_lang, target_lang,
                    translated_text, created_at, provider)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (cache_key, source_text, source_lang, target_lang,
                 translated_text, int(time.time()), provider),
            )
            conn.commit()
        _log.debug("Translation cached: %s...", source_text[:30])
    except Exception as e:
        _log.warning("Translation cache write error: %s", e)


# ============================================================================
# Lyrics cache
# ============================================================================

def get_lyrics_cache(
    track_title: str,
    artist: Optional[str] = None,
    isrc: Optional[str] = None,
) -> Optional[tuple[str, Optional[str], str]]:
    """
    Cek lyrics cache. Return tuple (synced_lyrics, plain_lyrics, provider)
    kalau ada, None kalau miss atau expired.

    Args:
        track_title: Judul lagu
        artist: Nama artist (opsional)
        isrc: ISRC code (opsional, paling akurat)

    Returns:
        Tuple (synced_lyrics, plain_lyrics, provider) kalau cache hit,
        None kalau miss atau expired.
    """
    cache_key = _hash_key(track_title, artist or "", isrc or "")
    try:
        with _LOCK, _get_connection() as conn:
            cursor = conn.execute(
                """SELECT synced_lyrics, plain_lyrics, provider, expires_at
                   FROM lyrics_cache WHERE cache_key = ?""",
                (cache_key,),
            )
            row = cursor.fetchone()
            if row is None:
                _log.debug("Lyrics cache MISS: %s", track_title[:30])
                return None

            synced, plain, provider, expires_at = row
            # Cek expiry
            if expires_at and int(time.time()) > expires_at:
                _log.debug("Lyrics cache EXPIRED: %s", track_title[:30])
                # Hapus entry expired
                conn.execute("DELETE FROM lyrics_cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
                return None

            _log.debug("Lyrics cache HIT: %s", track_title[:30])
            return (synced, plain, provider)
    except Exception as e:
        _log.warning("Lyrics cache read error: %s", e)
        return None


def set_lyrics_cache(
    track_title: str,
    synced_lyrics: str,
    plain_lyrics: Optional[str] = None,
    artist: Optional[str] = None,
    isrc: Optional[str] = None,
    provider: Optional[str] = None,
    ttl_seconds: int = _DEFAULT_TTL_SECONDS,
) -> None:
    """
    Simpan lyrics ke cache.

    Args:
        track_title: Judul lagu
        synced_lyrics: Lirik dengan timestamp (LRC format)
        plain_lyrics: Lirik tanpa timestamp (opsional)
        artist: Nama artist (opsional)
        isrc: ISRC code (opsional)
        provider: Nama provider yang memberikan lirik (mis. 'lrclib')
        ttl_seconds: Time-to-live dalam detik (default 30 hari)
    """
    cache_key = _hash_key(track_title, artist or "", isrc or "")
    expires_at = int(time.time()) + ttl_seconds if ttl_seconds > 0 else None
    try:
        with _LOCK, _get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO lyrics_cache
                   (cache_key, track_title, artist, isrc,
                    synced_lyrics, plain_lyrics, provider,
                    created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cache_key, track_title, artist, isrc,
                 synced_lyrics, plain_lyrics, provider,
                 int(time.time()), expires_at),
            )
            conn.commit()
        _log.debug("Lyrics cached: %s (TTL=%ds)", track_title[:30], ttl_seconds)
    except Exception as e:
        _log.warning("Lyrics cache write error: %s", e)


# ============================================================================
# Maintenance
# ============================================================================

def clear_expired_entries() -> int:
    """
    Hapus semua entry lyrics cache yang sudah expired.

    Returns:
        Jumlah entry yang dihapus.
    """
    try:
        with _LOCK, _get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM lyrics_cache WHERE expires_at IS NOT NULL AND expires_at < ?",
                (int(time.time()),),
            )
            deleted = cursor.rowcount
            conn.commit()
        if deleted > 0:
            _log.info("Cache cleanup: %d expired entries removed", deleted)
        return deleted
    except Exception as e:
        _log.warning("Cache cleanup error: %s", e)
        return 0


def get_cache_stats() -> dict:
    """
    Dapatkan statistik cache (untuk `mmpd doctor`).

    Returns:
        Dict dengan keys: 'translation_count', 'lyrics_count', 'db_size_bytes',
        'db_path'.
    """
    try:
        with _get_connection() as conn:
            t_count = conn.execute("SELECT COUNT(*) FROM translation_cache").fetchone()[0]
            l_count = conn.execute("SELECT COUNT(*) FROM lyrics_cache").fetchone()[0]
        db_path = _get_db_path()
        db_size = db_path.stat().st_size if db_path.exists() else 0
        return {
            "translation_count": t_count,
            "lyrics_count": l_count,
            "db_size_bytes": db_size,
            "db_path": str(db_path),
        }
    except Exception as e:
        _log.warning("Cache stats error: %s", e)
        return {
            "translation_count": 0,
            "lyrics_count": 0,
            "db_size_bytes": 0,
            "db_path": str(_get_db_path()),
            "error": str(e),
        }


def clear_all_cache() -> None:
    """Hapus SEMUA entry cache (untuk testing atau reset)."""
    try:
        with _LOCK, _get_connection() as conn:
            conn.execute("DELETE FROM translation_cache")
            conn.execute("DELETE FROM lyrics_cache")
            conn.commit()
        _log.info("All cache cleared")
    except Exception as e:
        _log.warning("Cache clear error: %s", e)


def reset_cache_singleton() -> None:
    """Reset DB path singleton (untuk testing)."""
    global _DB_PATH
    _DB_PATH = None
