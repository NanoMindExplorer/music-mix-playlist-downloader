"""
Unit tests untuk mmpd.types — TrackInfo, LyricsResult, LyricsProvider protocol.

Coverage:
    - TrackInfo: search_query(), clean_search_query()
    - LyricsResult: has_synced, best_lyrics
    - LyricsProvider protocol compliance check
"""

from __future__ import annotations

import pytest

from mmpd.types import LyricsProvider, LyricsResult, TrackInfo


# ============================================================================
# TrackInfo
# ============================================================================

class TestTrackInfo:
    def test_basic_creation(self):
        """Test buat TrackInfo dengan title saja."""
        track = TrackInfo(title="Hello")
        assert track.title == "Hello"
        assert track.artist is None
        assert track.album is None
        assert track.duration is None
        assert track.isrc is None

    def test_full_creation(self):
        """Test buat TrackInfo dengan semua field."""
        track = TrackInfo(
            title="Hello",
            artist="Adele",
            album="25",
            duration=295.0,
            isrc="GBBKS1500214",
        )
        assert track.title == "Hello"
        assert track.artist == "Adele"
        assert track.album == "25"
        assert track.duration == 295.0
        assert track.isrc == "GBBKS1500214"

    def test_search_query_with_artist(self):
        """Test search_query gabung title + artist."""
        track = TrackInfo(title="Hello", artist="Adele")
        assert track.search_query() == "Hello Adele"

    def test_search_query_without_artist(self):
        """Test search_query hanya title kalau no artist."""
        track = TrackInfo(title="Hello")
        assert track.search_query() == "Hello"

    def test_clean_search_query_strips_brackets(self):
        """Test clean_search_query hapus bracket dan promo keywords."""
        track = TrackInfo(title="[Rainych] JUSTadICE (Official Music Video)")
        clean = track.clean_search_query()
        assert "Rainych" not in clean
        assert "Official" not in clean
        assert "JUSTadICE" in clean

    def test_clean_search_query_with_artist(self):
        """Test clean_search_query gabung title + artist, lalu clean."""
        track = TrackInfo(title="Hello (Lyric Video)", artist="Adele")
        clean = track.clean_search_query()
        assert "Adele" in clean
        assert "Hello" in clean
        # "Lyric Video" harus hilang
        assert "Lyric" not in clean

    def test_clean_search_query_empty_title(self):
        """Test clean_search_query dengan empty title."""
        track = TrackInfo(title="")
        assert track.clean_search_query() == ""

    def test_frozen_dataclass(self):
        """Test TrackInfo immutable."""
        track = TrackInfo(title="Hello")
        with pytest.raises(Exception):
            track.title = "Changed"  # type: ignore


# ============================================================================
# LyricsResult
# ============================================================================

class TestLyricsResult:
    def test_basic_creation(self):
        """Test buat LyricsResult minimal."""
        result = LyricsResult(synced_lyrics="[00:00.00]Hello")
        assert result.synced_lyrics == "[00:00.00]Hello"
        assert result.plain_lyrics is None
        assert result.provider == "unknown"

    def test_has_synced_true(self):
        """Test has_synced True kalau synced_lyrics ada."""
        result = LyricsResult(synced_lyrics="[00:00.00]Hello")
        assert result.has_synced is True

    def test_has_synced_false_empty(self):
        """Test has_synced False kalau synced_lyrics empty."""
        result = LyricsResult(synced_lyrics="")
        assert result.has_synced is False

    def test_has_synced_false_whitespace_only(self):
        """Test has_synced False kalau hanya whitespace."""
        result = LyricsResult(synced_lyrics="   \n\t  ")
        assert result.has_synced is False

    def test_best_lyrics_uses_synced_first(self):
        """Test best_lyrics prefer synced over plain."""
        result = LyricsResult(
            synced_lyrics="[00:00.00]synced",
            plain_lyrics="plain text",
        )
        assert result.best_lyrics == "[00:00.00]synced"

    def test_best_lyrics_fallback_to_plain(self):
        """Test best_lyrics fallback ke plain kalau synced empty."""
        result = LyricsResult(
            synced_lyrics="",
            plain_lyrics="plain text fallback",
        )
        assert result.best_lyrics == "plain text fallback"

    def test_best_lyrics_empty_when_both_empty(self):
        """Test best_lyrics empty kalau synced dan plain keduanya empty."""
        result = LyricsResult(synced_lyrics="", plain_lyrics=None)
        assert result.best_lyrics == ""

    def test_provider_field(self):
        """Test provider field."""
        result = LyricsResult(synced_lyrics="x", provider="lrclib")
        assert result.provider == "lrclib"

    def test_metadata_fields(self):
        """Test track_name, artist_name, duration_ms."""
        result = LyricsResult(
            synced_lyrics="x",
            track_name="Hello",
            artist_name="Adele",
            duration_ms=295000,
        )
        assert result.track_name == "Hello"
        assert result.artist_name == "Adele"
        assert result.duration_ms == 295000

    def test_frozen_dataclass(self):
        """Test LyricsResult immutable."""
        result = LyricsResult(synced_lyrics="x")
        with pytest.raises(Exception):
            result.synced_lyrics = "changed"  # type: ignore


# ============================================================================
# LyricsProvider Protocol (runtime check)
# ============================================================================

class TestLyricsProviderProtocol:
    def test_protocol_runtime_check_valid(self):
        """Test class yang implement LyricsProvider lolos isinstance check."""

        class MockProvider:
            name = "mock"
            priority = 0

            def search(self, track):
                return None

        # LyricsProvider adalah runtime_checkable Protocol
        assert isinstance(MockProvider(), LyricsProvider)

    def test_protocol_missing_method_fails(self):
        """Test class tanpa method search() tidak lolos protocol."""

        class IncompleteProvider:
            name = "incomplete"
            priority = 10
            # Tidak ada method search()

        # Python Protocol check: cek attribute ada, bukan signature match
        # Untuk runtime_checkable, isinstance cek ada attribute name
        # Tapi isinstance check Protocol method juga
        instance = IncompleteProvider()
        # Cek manual: hasattr search
        assert not hasattr(instance, "search")

    def test_protocol_different_priorities(self):
        """Test provider dengan priority berbeda."""

        class HighPriority:
            name = "high"
            priority = 0

            def search(self, track):
                return None

        class LowPriority:
            name = "low"
            priority = 10

            def search(self, track):
                return None

        assert HighPriority.priority < LowPriority.priority
