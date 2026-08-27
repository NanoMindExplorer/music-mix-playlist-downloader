"""
Unit tests untuk mmpd.spotify_client — SpotifyClient + SpotifyTrack.

Strategy:
    - Mock spotipy module supaya tidak butuh credentials real
    - Test SpotifyTrack dataclass + conversion methods
    - Test SpotifyClient.is_available (env vars check)
    - Test _parse_spotify_url pattern matching
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# SpotifyTrack dataclass
# ============================================================================

class TestSpotifyTrack:
    def test_basic_creation(self):
        """Test buat SpotifyTrack minimal."""
        from mmpd.spotify_client import SpotifyTrack
        track = SpotifyTrack(title="Hello", artist="Adele")
        assert track.title == "Hello"
        assert track.artist == "Adele"
        assert track.isrc is None
        assert track.duration_ms is None

    def test_full_creation(self, mock_spotify_track):
        """Test SpotifyTrack dengan semua field."""
        assert mock_spotify_track.title == "Hello"
        assert mock_spotify_track.artist == "Adele"
        assert mock_spotify_track.album == "25"
        assert mock_spotify_track.duration_ms == 295000
        assert mock_spotify_track.isrc == "GBBKS1500214"
        assert mock_spotify_track.explicit is False
        assert mock_spotify_track.popularity == 85

    def test_to_track_info_conversion(self, mock_spotify_track):
        """Test konversi SpotifyTrack → TrackInfo."""
        track_info = mock_spotify_track.to_track_info()
        assert track_info.title == "Hello"
        assert track_info.artist == "Adele"
        assert track_info.album == "25"
        assert track_info.duration == 295.0  # 295000ms → 295.0s
        assert track_info.isrc == "GBBKS1500214"

    def test_to_ytsearch_query(self, mock_spotify_track):
        """Test bangun query ytsearch."""
        query = mock_spotify_track.to_ytsearch_query()
        assert "Hello" in query
        assert "Adele" in query

    def test_to_ytsearch_query_no_artist(self):
        """Test query dengan artist kosong."""
        from mmpd.spotify_client import SpotifyTrack
        track = SpotifyTrack(title="Instrumental", artist="")
        query = track.to_ytsearch_query()
        # Title tetap ada, artist kosong tidak menambah apa-apa
        assert "Instrumental" in query

    def test_frozen_dataclass(self, mock_spotify_track):
        """Test SpotifyTrack immutable."""
        with pytest.raises(Exception):
            mock_spotify_track.title = "Changed"  # type: ignore

    def test_to_track_info_no_duration(self):
        """Test konversi tanpa duration_ms."""
        from mmpd.spotify_client import SpotifyTrack
        track = SpotifyTrack(title="Test", artist="Artist")
        track_info = track.to_track_info()
        assert track_info.duration is None


# ============================================================================
# SpotifyClient — is_available check
# ============================================================================

class TestSpotifyClientAvailability:
    def test_not_available_without_env_vars(self, monkeypatch):
        """Test is_available False kalau env vars tidak ada."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        from mmpd.spotify_client import SpotifyClient
        client = SpotifyClient()
        assert client.is_available is False

    def test_not_available_with_only_client_id(self, monkeypatch):
        """Test is_available False kalau hanya CLIENT_ID yang set."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id")
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        from mmpd.spotify_client import SpotifyClient
        client = SpotifyClient()
        assert client.is_available is False

    def test_not_available_with_only_secret(self, monkeypatch):
        """Test is_available False kalau hanya SECRET yang set."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret")

        from mmpd.spotify_client import SpotifyClient
        client = SpotifyClient()
        assert client.is_available is False

    def test_available_with_credentials_and_spotipy(self, monkeypatch):
        """Test is_available True kalau env vars ada + spotipy terinstal."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "valid_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "valid_secret_1234567890")

        # Mock spotipy module
        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd.spotify_client import SpotifyClient
            client = SpotifyClient()
            assert client.is_available is True

    def test_not_available_if_spotipy_not_installed(self, monkeypatch):
        """Test is_available False kalau spotipy tidak terinstal."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "valid_id")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "valid_secret")

        # Remove spotipy from sys.modules
        import sys
        original_spotipy = sys.modules.pop("spotipy", None)
        try:
            # Mock import to raise ImportError
            with patch.dict("sys.modules", {"spotipy": None}):
                from mmpd.spotify_client import SpotifyClient
                client = SpotifyClient()
                # When sys.modules[key] = None, import raises ImportError
                assert client.is_available is False
        finally:
            if original_spotipy is not None:
                sys.modules["spotipy"] = original_spotipy


# ============================================================================
# SpotifyClient — _parse_spotify_url pattern matching
# ============================================================================

class TestParseSpotifyUrl:
    def test_parse_track_url(self):
        """Test parse URL track Spotify."""
        from mmpd.spotify_client import SpotifyClient
        result = SpotifyClient._parse_spotify_url(
            "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
        )
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_parse_album_url(self):
        """Test parse URL album."""
        from mmpd.spotify_client import SpotifyClient
        result = SpotifyClient._parse_spotify_url(
            "https://open.spotify.com/album/7sgtqAGcd9SunLOdnx3SJm"
        )
        assert result == ("album", "7sgtqAGcd9SunLOdnx3SJm")

    def test_parse_playlist_url(self):
        """Test parse URL playlist."""
        from mmpd.spotify_client import SpotifyClient
        result = SpotifyClient._parse_spotify_url(
            "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
        )
        assert result == ("playlist", "37i9dQZF1DXcBWIGoYBM5M")

    def test_parse_intl_prefixed_url(self):
        """Test parse URL dengan intl- prefix (locale redirect)."""
        from mmpd.spotify_client import SpotifyClient
        result = SpotifyClient._parse_spotify_url(
            "https://open.spotify.com/intl-id/track/4uLU6hMCjMI75M1A2tKUQC"
        )
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_parse_url_with_query_params(self):
        """Test parse URL dengan query parameters (si=presaved)."""
        from mmpd.spotify_client import SpotifyClient
        result = SpotifyClient._parse_spotify_url(
            "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC?si=abc123"
        )
        assert result == ("track", "4uLU6hMCjMI75M1A2tKUQC")

    def test_parse_invalid_url_returns_none(self):
        """Test parse URL non-Spotify return None."""
        from mmpd.spotify_client import SpotifyClient
        result = SpotifyClient._parse_spotify_url("https://youtube.com/watch?v=abc")
        assert result is None

    def test_parse_empty_string_returns_none(self):
        """Test parse empty string return None."""
        from mmpd.spotify_client import SpotifyClient
        result = SpotifyClient._parse_spotify_url("")
        assert result is None


# ============================================================================
# SpotifyClient — _parse_track_response
# ============================================================================

class TestParseTrackResponse:
    def test_parse_full_track_response(self):
        """Test parse response track lengkap dari Spotify API."""
        from mmpd.spotify_client import SpotifyClient
        mock_data = {
            "name": "Hello",
            "artists": [{"name": "Adele"}],
            "album": {"name": "25"},
            "duration_ms": 295000,
            "external_ids": {"isrc": "GBBKS1500214"},
            "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
            "popularity": 85,
            "explicit": False,
        }

        result = SpotifyClient._parse_track_response(mock_data)
        assert result is not None
        assert result.title == "Hello"
        assert result.artist == "Adele"
        assert result.album == "25"
        assert result.duration_ms == 295000
        assert result.isrc == "GBBKS1500214"
        assert result.popularity == 85

    def test_parse_track_with_multiple_artists(self):
        """Test parse track dengan multiple artists (kolaborasi)."""
        from mmpd.spotify_client import SpotifyClient
        mock_data = {
            "name": "Collab Song",
            "artists": [{"name": "Artist A"}, {"name": "Artist B"}, {"name": "Artist C"}],
            "album": {"name": "Various"},
            "duration_ms": 200000,
            "external_ids": {},
        }

        result = SpotifyClient._parse_track_response(mock_data)
        assert result is not None
        # Artists should be joined with ", "
        assert result.artist == "Artist A, Artist B, Artist C"

    def test_parse_track_without_isrc(self):
        """Test parse track tanpa ISRC."""
        from mmpd.spotify_client import SpotifyClient
        mock_data = {
            "name": "No ISRC Song",
            "artists": [{"name": "Artist"}],
            "duration_ms": 180000,
            "external_ids": {},  # No ISRC
        }

        result = SpotifyClient._parse_track_response(mock_data)
        assert result is not None
        assert result.isrc is None

    def test_parse_track_without_album(self):
        """Test parse track tanpa album info."""
        from mmpd.spotify_client import SpotifyClient
        mock_data = {
            "name": "Single",
            "artists": [{"name": "Artist"}],
            "duration_ms": 200000,
            "external_ids": {"isrc": "US123456789"},
        }

        result = SpotifyClient._parse_track_response(mock_data)
        assert result is not None
        assert result.album is None

    def test_parse_empty_data_returns_none(self):
        """Test parse empty/None data return None."""
        from mmpd.spotify_client import SpotifyClient
        assert SpotifyClient._parse_track_response(None) is None
        assert SpotifyClient._parse_track_response({}) is None

    def test_parse_track_without_name_returns_none(self):
        """Test parse track tanpa name return None."""
        from mmpd.spotify_client import SpotifyClient
        mock_data = {
            "artists": [{"name": "Artist"}],
            "duration_ms": 200000,
        }
        result = SpotifyClient._parse_track_response(mock_data)
        assert result is None


# ============================================================================
# SpotifyClient — _call_with_retry (exponential backoff)
# ============================================================================

class TestCallWithRetry:
    def test_retry_succeeds_on_second_attempt(self, monkeypatch):
        """Test retry sukses di attempt kedua."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        # Mock spotipy
        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd.spotify_client import SpotifyClient
            client = SpotifyClient()

            # Mock function yang gagal pertama, sukses kedua
            call_count = [0]

            def flaky_call():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise ConnectionError("Network error")
                return "success"

            # Mock time.sleep untuk skip wait
            with patch("time.sleep"):
                result = client._call_with_retry(flaky_call, max_retries=3)
                assert result == "success"
                assert call_count[0] == 2

    def test_retry_exhausted_returns_none(self, monkeypatch):
        """Test retry habis return None."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd.spotify_client import SpotifyClient
            client = SpotifyClient()

            def always_fail():
                raise ConnectionError("Always fails")

            with patch("time.sleep"):
                result = client._call_with_retry(always_fail, max_retries=2)
                assert result is None

    def test_non_retryable_exception_returns_none(self, monkeypatch):
        """Test exception non-retryable (ValueError) langsung return None."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd.spotify_client import SpotifyClient
            client = SpotifyClient()

            def raise_value_error():
                raise ValueError("Bad request - non retryable")

            result = client._call_with_retry(raise_value_error, max_retries=3)
            assert result is None


# ============================================================================
# Singleton
# ============================================================================

class TestSpotifyClientSingleton:
    def test_get_spotify_client_returns_instance(self):
        """Test get_spotify_client return instance."""
        from mmpd.spotify_client import get_spotify_client, SpotifyClient
        client = get_spotify_client()
        assert isinstance(client, SpotifyClient)

    def test_get_spotify_client_returns_same_instance(self):
        """Test singleton return instance yang sama."""
        from mmpd.spotify_client import get_spotify_client
        c1 = get_spotify_client()
        c2 = get_spotify_client()
        assert c1 is c2

    def test_reset_spotify_client(self):
        """Test reset membuat instance baru."""
        from mmpd.spotify_client import get_spotify_client, reset_spotify_client
        c1 = get_spotify_client()
        reset_spotify_client()
        c2 = get_spotify_client()
        assert c1 is not c2
