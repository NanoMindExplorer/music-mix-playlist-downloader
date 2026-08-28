"""
Unit tests untuk mmpd.lyrics_providers — LrclibProvider + SyncedLyricsProvider + LyricsChain.

Strategy:
    - Mock requests module untuk LrclibProvider (no real HTTP)
    - Mock syncedlyrics.search untuk SyncedLyricsProvider
    - Test LyricsChain fallback chain behavior
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from mmpd.types import LyricsResult, TrackInfo


# ============================================================================
# LrclibProvider
# ============================================================================

class TestLrclibProvider:
    def test_provider_name_and_priority(self):
        """Test name='lrclib', priority=0 (highest)."""
        from mmpd.lyrics_providers import LrclibProvider
        provider = LrclibProvider()
        assert provider.name == "lrclib"
        assert provider.priority == 0

    def test_search_by_isrc_match(self, mock_track_info):
        """Test search by ISRC — return result kalau ISRC match."""
        from mmpd.lyrics_providers import LrclibProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "syncedLyrics": "[00:00.00]Hello world",
            "plainLyrics": "Hello world plain",
            "trackName": "Hello",
            "artistName": "Adele",
            "duration": 295000,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("mmpd.lyrics_providers.requests", create=True) as mock_requests_mod:
            # Karena LrclibProvider lazy import requests di dalam search(),
            # kita patch sys.modules agar import requests return mock
            import sys
            mock_requests = MagicMock()
            mock_requests.get.return_value = mock_response
            sys.modules["requests"] = mock_requests

            try:
                provider = LrclibProvider()
                result = provider.search(mock_track_info)
            finally:
                # Restore original requests module
                if "requests" in sys.modules:
                    del sys.modules["requests"]
                # Re-import real requests
                import importlib
                if "mmpd.lyrics_providers" in sys.modules:
                    del sys.modules["mmpd.lyrics_providers"]

        if result:
            assert result.provider == "lrclib"
            assert result.has_synced
            assert result.track_name == "Hello"

    def test_search_returns_none_on_404(self, mock_track_info):
        """Test search return None kalau API return 404."""
        from mmpd.lyrics_providers import LrclibProvider

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        # Inject mock requests ke sys.modules sebelum LrclibProvider search()
        import sys
        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_response
        sys.modules["requests"] = mock_requests

        try:
            provider = LrclibProvider()
            result = provider.search(mock_track_info)
        finally:
            if "requests" in sys.modules:
                del sys.modules["requests"]
            if "mmpd.lyrics_providers" in sys.modules:
                del sys.modules["mmpd.lyrics_providers"]

        # Result should be None (404 = no match)
        assert result is None

    def test_search_handles_network_error(self, mock_track_info):
        """Test search return None kalau network error."""
        from mmpd.lyrics_providers import LrclibProvider

        import sys
        mock_requests = MagicMock()
        mock_requests.get.side_effect = ConnectionError("Network down")
        sys.modules["requests"] = mock_requests

        try:
            provider = LrclibProvider()
            result = provider.search(mock_track_info)
        finally:
            if "requests" in sys.modules:
                del sys.modules["requests"]
            if "mmpd.lyrics_providers" in sys.modules:
                del sys.modules["mmpd.lyrics_providers"]

        assert result is None

    def test_search_returns_none_for_empty_title(self):
        """Test search dengan empty title return None."""
        from mmpd.lyrics_providers import LrclibProvider

        track = TrackInfo(title="")
        provider = LrclibProvider()

        # Patch requests supaya tidak benar-benar hit network
        import sys
        mock_requests = MagicMock()
        mock_requests.get.return_value = MagicMock(status_code=404)
        sys.modules["requests"] = mock_requests

        try:
            result = provider.search(track)
        finally:
            if "requests" in sys.modules:
                del sys.modules["requests"]
            if "mmpd.lyrics_providers" in sys.modules:
                del sys.modules["mmpd.lyrics_providers"]

        # Empty title → no valid query → None
        assert result is None

    def test_parse_response_empty_data(self):
        """Test _parse_lrclib_response dengan empty dict return None."""
        from mmpd.lyrics_providers import LrclibProvider

        result = LrclibProvider._parse_lrclib_response({})
        assert result is None

        result = LrclibProvider._parse_lrclib_response(None)
        assert result is None


# ============================================================================
# SyncedLyricsProvider
# ============================================================================

class TestSyncedLyricsProvider:
    def test_provider_name_and_priority(self):
        """Test name='syncedlyrics', priority=10."""
        from mmpd.lyrics_providers import SyncedLyricsProvider
        provider = SyncedLyricsProvider()
        assert provider.name == "syncedlyrics"
        assert provider.priority == 10

    def test_search_with_results(self, mock_track_info):
        """Test search return LyricsResult kalau syncedlyrics.search return text."""
        from mmpd.lyrics_providers import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        # Mock the lazy init: set _search_fn manual
        provider._search_fn = MagicMock(return_value="[00:00.00]Hello world")
        provider._initialized = True

        result = provider.search(mock_track_info)
        assert result is not None
        assert result.provider == "syncedlyrics"
        assert result.has_synced
        assert "Hello world" in result.synced_lyrics

    def test_search_returns_none_when_no_match(self, mock_track_info):
        """Test search return None kalau syncedlyrics.search return None/empty."""
        from mmpd.lyrics_providers import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._search_fn = MagicMock(return_value=None)
        provider._initialized = True

        result = provider.search(mock_track_info)
        assert result is None

    def test_search_with_empty_string_response(self, mock_track_info):
        """Test search return None kalau syncedlyrics return empty string."""
        from mmpd.lyrics_providers import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._search_fn = MagicMock(return_value="")
        provider._initialized = True

        result = provider.search(mock_track_info)
        assert result is None

    def test_search_retries_with_raw_query(self, mock_track_info):
        """Test search retry dengan raw query kalau clean query gagal."""
        from mmpd.lyrics_providers import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        # First call (clean) return None, second call (raw) return text
        provider._search_fn = MagicMock(side_effect=[None, "[00:00.00]Found"])
        provider._initialized = True

        # Pakai track dengan title yang berbeda setelah clean
        track = TrackInfo(title="[Artist] Song (Official Video)")
        result = provider.search(track)
        assert result is not None
        assert "Found" in result.synced_lyrics

    def test_search_handles_exception(self, mock_track_info):
        """Test search return None kalau syncedlyrics.search raise exception."""
        from mmpd.lyrics_providers import SyncedLyricsProvider

        provider = SyncedLyricsProvider()
        provider._search_fn = MagicMock(side_effect=Exception("Network error"))
        provider._initialized = True

        result = provider.search(mock_track_info)
        assert result is None


# ============================================================================
# LyricsChain
# ============================================================================

class TestLyricsChain:
    def test_chain_returns_first_success(self, mock_track_info):
        """Test chain return result dari provider pertama yang sukses."""

        class FirstProvider:
            name = "first"
            priority = 0
            def search(self, track):
                return LyricsResult(synced_lyrics="from first", provider="first")

        class SecondProvider:
            name = "second"
            priority = 10
            def search(self, track):
                return LyricsResult(synced_lyrics="from second", provider="second")

        from mmpd.lyrics_providers import LyricsChain
        chain = LyricsChain([FirstProvider(), SecondProvider()])
        result = chain.search(mock_track_info)
        assert result is not None
        assert result.provider == "first"

    def test_chain_fallback_to_next_provider(self, mock_track_info):
        """Test chain fallback kalau provider pertama gagal."""

        class FailingProvider:
            name = "fail"
            priority = 0
            def search(self, track):
                return None

        class SuccessProvider:
            name = "success"
            priority = 10
            def search(self, track):
                return LyricsResult(synced_lyrics="from success", provider="success")

        from mmpd.lyrics_providers import LyricsChain
        chain = LyricsChain([FailingProvider(), SuccessProvider()])
        result = chain.search(mock_track_info)
        assert result is not None
        assert result.provider == "success"

    def test_chain_returns_none_when_all_fail(self, mock_track_info):
        """Test chain return None kalau semua provider gagal."""

        class FailingProvider1:
            name = "fail1"
            priority = 0
            def search(self, track):
                return None

        class FailingProvider2:
            name = "fail2"
            priority = 10
            def search(self, track):
                return None

        from mmpd.lyrics_providers import LyricsChain
        chain = LyricsChain([FailingProvider1(), FailingProvider2()])
        result = chain.search(mock_track_info)
        assert result is None

    def test_chain_isolates_exceptions(self, mock_track_info):
        """Test chain tetap jalan walau satu provider raise exception."""

        class CrashingProvider:
            name = "crash"
            priority = 0
            def search(self, track):
                raise RuntimeError("Crash!")

        class GoodProvider:
            name = "good"
            priority = 10
            def search(self, track):
                return LyricsResult(synced_lyrics="recovered", provider="good")

        from mmpd.lyrics_providers import LyricsChain
        chain = LyricsChain([CrashingProvider(), GoodProvider()])
        result = chain.search(mock_track_info)
        # Should not raise, should return result from GoodProvider
        assert result is not None
        assert result.provider == "good"

    def test_chain_sorts_by_priority(self, mock_track_info):
        """Test chain sort providers by priority ascending."""
        # Provider priority lebih kecil = lebih dulu

        class Priority5:
            name = "p5"
            priority = 5
            def search(self, track):
                return LyricsResult(synced_lyrics="p5", provider="p5")

        class Priority0:
            name = "p0"
            priority = 0
            def search(self, track):
                return LyricsResult(synced_lyrics="p0", provider="p0")

        class Priority10:
            name = "p10"
            priority = 10
            def search(self, track):
                return LyricsResult(synced_lyrics="p10", provider="p10")

        from mmpd.lyrics_providers import LyricsChain
        # Sengaja input tidak urut
        chain = LyricsChain([Priority10(), Priority5(), Priority0()])
        result = chain.search(mock_track_info)
        # Should pick priority=0 first
        assert result.provider == "p0"


# ============================================================================
# build_default_chain
# ============================================================================

class TestBuildDefaultChain:
    def test_default_chain_has_two_providers(self):
        """Test default chain punya LRCLIB + syncedlyrics."""
        from mmpd.lyrics_providers import build_default_chain
        chain = build_default_chain()
        assert len(chain._providers) == 3

    def test_default_chain_lrclib_first(self):
        """Test LRCLIB ada di urutan pertama (priority=0)."""
        from mmpd.lyrics_providers import build_default_chain
        chain = build_default_chain()
        assert chain._providers[0].name == "lrclib"
        assert chain._providers[0].priority == 0

    def test_default_chain_syncedlyrics_second(self):
        """Test syncedlyrics ada di urutan kedua (priority=10)."""
        from mmpd.lyrics_providers import build_default_chain
        chain = build_default_chain()
        assert chain._providers[1].name == "musixmatch_native"
        assert chain._providers[2].name == "syncedlyrics"
        assert chain._providers[2].priority == 10
