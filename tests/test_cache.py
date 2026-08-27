"""
Unit tests untuk mmpd.cache — translation + lyrics cache (SQLite).

Strategy:
    - Pakai tmp_path fixture untuk isolated DB per test
    - Mock cache DB path via reset_cache_singleton + patch _get_db_path
    - Test cache hit/miss/expire
    - Test clear_expired_entries + get_cache_stats
"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest


# ============================================================================
# Translation cache
# ============================================================================

class TestTranslationCache:
    def test_cache_miss_returns_none(self, tmp_path, mock_linux_env):
        """Test cache miss return None."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            result = cache_mod.get_translation_cache("hello world", "en", "id")
        assert result is None

    def test_cache_set_then_get_hit(self, tmp_path, mock_linux_env):
        """Test set cache lalu get hit."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_translation_cache("hello", "en", "id", "halo", provider="google")
            result = cache_mod.get_translation_cache("hello", "en", "id")
        assert result == "halo"

    def test_cache_different_target_lang_miss(self, tmp_path, mock_linux_env):
        """Test cache miss kalau target_lang berbeda."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_translation_cache("hello", "en", "id", "halo")
            # Different target_lang → miss
            result = cache_mod.get_translation_cache("hello", "en", "ja")
        assert result is None

    def test_cache_different_source_text_miss(self, tmp_path, mock_linux_env):
        """Test cache miss kalau source_text berbeda."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_translation_cache("hello", "en", "id", "halo")
            # Different source_text → miss
            result = cache_mod.get_translation_cache("goodbye", "en", "id")
        assert result is None

    def test_cache_overwrite_on_set(self, tmp_path, mock_linux_env):
        """Test set overwrite entry yang sudah ada."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_translation_cache("hello", "en", "id", "halo v1")
            cache_mod.set_translation_cache("hello", "en", "id", "halo v2")
            result = cache_mod.get_translation_cache("hello", "en", "id")
        assert result == "halo v2"

    def test_cache_unicode_text(self, tmp_path, mock_linux_env):
        """Test cache dengan Unicode text (CJK, emoji)."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        unicode_text = "こんにちは世界 🌍 مرحبا بالعالم"
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_translation_cache(unicode_text, "auto", "id", "halo dunia")
            result = cache_mod.get_translation_cache(unicode_text, "auto", "id")
        assert result == "halo dunia"

    def test_cache_persists_across_connections(self, tmp_path, mock_linux_env):
        """Test cache persists walau koneksi SQLite berbeda."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        db_path = tmp_path / "persist.db"
        # Set dengan satu koneksi
        with patch.object(cache_mod, "_get_db_path", return_value=db_path):
            cache_mod.set_translation_cache("test", "en", "id", "tes")
        # Reset singleton, get dengan koneksi baru
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=db_path):
            result = cache_mod.get_translation_cache("test", "en", "id")
        assert result == "tes"


# ============================================================================
# Lyrics cache
# ============================================================================

class TestLyricsCache:
    def test_cache_miss_returns_none(self, tmp_path, mock_linux_env):
        """Test lyrics cache miss."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            result = cache_mod.get_lyrics_cache("Hello", artist="Adele")
        assert result is None

    def test_cache_set_then_get_hit(self, tmp_path, mock_linux_env):
        """Test lyrics cache hit."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_lyrics_cache(
                track_title="Hello",
                synced_lyrics="[00:00.00]Hello world",
                plain_lyrics="Hello world",
                artist="Adele",
                isrc="GBBKS1500214",
                provider="lrclib",
            )
            result = cache_mod.get_lyrics_cache("Hello", artist="Adele", isrc="GBBKS1500214")
        assert result is not None
        synced, plain, provider = result
        assert "[00:00.00]Hello world" in synced
        assert "Hello world" in plain
        assert provider == "lrclib"

    def test_cache_expired_returns_none(self, tmp_path, mock_linux_env):
        """Test lyrics cache expired entry return None."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            # Set dengan TTL sangat singkat (1 detik)
            cache_mod.set_lyrics_cache(
                track_title="Test Song",
                synced_lyrics="lyrics",
                ttl_seconds=1,
            )
            # Wait 2 seconds supaya expired
            time.sleep(2)
            result = cache_mod.get_lyrics_cache("Test Song")
        assert result is None

    def test_cache_no_ttl_never_expires(self, tmp_path, mock_linux_env):
        """Test lyrics cache tanpa TTL tidak pernah expire."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_lyrics_cache(
                track_title="Permanent",
                synced_lyrics="lyrics",
                ttl_seconds=0,  # 0 = no expiry
            )
            result = cache_mod.get_lyrics_cache("Permanent")
        assert result is not None

    def test_cache_different_isrc_miss(self, tmp_path, mock_linux_env):
        """Test cache miss kalau ISRC berbeda."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_lyrics_cache(
                track_title="Hello",
                synced_lyrics="lyrics",
                isrc="ISRC1",
            )
            # Different ISRC → miss
            result = cache_mod.get_lyrics_cache("Hello", isrc="ISRC2")
        assert result is None


# ============================================================================
# Maintenance: clear_expired_entries, get_cache_stats, clear_all_cache
# ============================================================================

class TestCacheMaintenance:
    def test_clear_expired_entries(self, tmp_path, mock_linux_env):
        """Test hapus expired entries."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            # Set 2 entries: 1 expired, 1 fresh
            cache_mod.set_lyrics_cache("Expired", "lyrics", ttl_seconds=1)
            cache_mod.set_lyrics_cache("Fresh", "lyrics", ttl_seconds=3600)
            time.sleep(2)
            deleted = cache_mod.clear_expired_entries()
        assert deleted == 1

    def test_clear_expired_no_entries(self, tmp_path, mock_linux_env):
        """Test clear_expired dengan empty cache."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            deleted = cache_mod.clear_expired_entries()
        assert deleted == 0

    def test_get_cache_stats_empty(self, tmp_path, mock_linux_env):
        """Test get_cache_stats dengan empty cache."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            stats = cache_mod.get_cache_stats()
        assert stats["translation_count"] == 0
        assert stats["lyrics_count"] == 0

    def test_get_cache_stats_with_entries(self, tmp_path, mock_linux_env):
        """Test get_cache_stats dengan beberapa entries."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_translation_cache("hello", "en", "id", "halo")
            cache_mod.set_lyrics_cache("Hello", "lyrics", artist="Adele")
            cache_mod.set_lyrics_cache("World", "lyrics", artist="Someone")
            stats = cache_mod.get_cache_stats()
        assert stats["translation_count"] == 1
        assert stats["lyrics_count"] == 2
        assert stats["db_size_bytes"] > 0
        assert "test.db" in stats["db_path"]

    def test_clear_all_cache(self, tmp_path, mock_linux_env):
        """Test clear_all_cache hapus semua entries."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        with patch.object(cache_mod, "_get_db_path", return_value=tmp_path / "test.db"):
            cache_mod.set_translation_cache("hello", "en", "id", "halo")
            cache_mod.set_lyrics_cache("Hello", "lyrics")
            cache_mod.clear_all_cache()
            stats = cache_mod.get_cache_stats()
        assert stats["translation_count"] == 0
        assert stats["lyrics_count"] == 0

    def test_reset_cache_singleton(self, mock_linux_env):
        """Test reset_cache_singleton reset DB path."""
        from mmpd import cache as cache_mod
        cache_mod.reset_cache_singleton()
        # Should not raise
        cache_mod.reset_cache_singleton()


# ============================================================================
# Hash key function
# ============================================================================

class TestHashKey:
    def test_hash_consistent(self):
        """Test hash konsisten untuk input yang sama."""
        from mmpd.cache import _hash_key
        h1 = _hash_key("hello", "en", "id")
        h2 = _hash_key("hello", "en", "id")
        assert h1 == h2

    def test_hash_different_inputs(self):
        """Test hash berbeda untuk input berbeda."""
        from mmpd.cache import _hash_key
        h1 = _hash_key("hello", "en", "id")
        h2 = _hash_key("world", "en", "id")
        assert h1 != h2

    def test_hash_returns_hex_string(self):
        """Test hash return hex string (64 chars untuk SHA256)."""
        from mmpd.cache import _hash_key
        h = _hash_key("test")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA256 hex digest
        # All chars should be hex digits
        assert all(c in "0123456789abcdef" for c in h)
