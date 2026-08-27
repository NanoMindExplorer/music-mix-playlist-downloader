"""
Unit tests untuk mmpd.spotify — parse_spotify_url_safe + parse_spotify_url_v2 + helpers.

Fase 5: legacy scraping dihapus. Tests sekarang fokus ke spotipy path.
Strategy:
    - Mock spotify_client.get_spotify_client untuk test spotipy path
    - Test is_spotify_url validator
    - Test build_ytsearch_query
    - Test spotipy_available (env vars check)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ============================================================================
# is_spotify_url
# ============================================================================

class TestIsSpotifyUrl:
    def test_valid_track_url(self):
        """Test valid track URL Spotify."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("https://open.spotify.com/track/abc123") is True

    def test_valid_playlist_url(self):
        """Test valid playlist URL."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("https://open.spotify.com/playlist/xyz789") is True

    def test_valid_album_url(self):
        """Test valid album URL."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("https://open.spotify.com/album/def456") is True

    def test_url_with_query_params(self):
        """Test URL dengan query params."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("https://open.spotify.com/track/abc?si=xxx") is True

    def test_intl_prefixed_url(self):
        """Test URL dengan intl- prefix."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("https://open.spotify.com/intl-id/track/abc") is True

    def test_youtube_url_returns_false(self):
        """Test URL YouTube return False."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("https://www.youtube.com/watch?v=abc") is False

    def test_empty_string_returns_false(self):
        """Test empty string return False."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("") is False

    def test_non_http_returns_false(self):
        """Test non-HTTP string return False."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("open.spotify.com/track/abc") is False  # No http prefix

    def test_spotify_without_open_returns_false(self):
        """Test URL dengan spotify.com tapi tanpa 'open' return False."""
        from mmpd.spotify import is_spotify_url
        assert is_spotify_url("https://spotify.com/track/abc") is False


# ============================================================================
# build_ytsearch_query
# ============================================================================

class TestBuildYtsearchQuery:
    def test_basic_query(self):
        """Test basic ytsearch query."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Adele Hello", limit=1)
        assert result == "ytsearch1:Adele Hello"

    def test_query_with_limit_3(self):
        """Test query dengan limit 3."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("Test Song", limit=3)
        assert result == "ytsearch3:Test Song"

    def test_query_clean_brackets(self):
        """Test query dengan bracket dibersihkan."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("[Artist] Song (Official)", limit=1)
        assert "ytsearch1:" in result
        assert "[" not in result
        assert "(" not in result

    def test_empty_query_after_clean(self):
        """Test empty query setelah clean pakai original."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("[Official]", limit=1)
        assert "ytsearch1:" in result


# ============================================================================
# spotipy_available
# ============================================================================

class TestSpotipyAvailable:
    def test_returns_false_without_credentials(self, monkeypatch):
        """Test spotipy_available return False tanpa credentials."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        from mmpd import spotify_client as sc
        sc.reset_spotify_client()
        from mmpd.spotify import spotipy_available
        assert spotipy_available() is False

    def test_returns_true_with_credentials(self, monkeypatch):
        """Test spotipy_available return True dengan credentials + spotipy terinstal."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()
            from mmpd.spotify import spotipy_available
            assert spotipy_available() is True


# ============================================================================
# parse_spotify_url_safe (return List[str])
# ============================================================================

class TestParseSpotifyUrlSafe:
    def test_non_spotify_url_returns_empty(self):
        """Test non-Spotify URL return empty list."""
        from mmpd.spotify import parse_spotify_url_safe
        result = parse_spotify_url_safe("https://youtube.com/watch?v=abc")
        assert result == []

    def test_returns_empty_without_credentials(self, monkeypatch):
        """Test return empty kalau spotipy tidak available (no credentials)."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        from mmpd import spotify_client as sc
        sc.reset_spotify_client()
        from mmpd.spotify import parse_spotify_url_safe
        result = parse_spotify_url_safe("https://open.spotify.com/playlist/abc")
        assert result == []

    def test_returns_queries_with_spotipy(self, monkeypatch):
        """Test return List[str] kalau spotipy available + berhasil parse."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()

            # Mock SpotifyClient.parse_url return tracks
            mock_track1 = MagicMock()
            mock_track1.to_ytsearch_query.return_value = "Adele Hello"
            mock_track2 = MagicMock()
            mock_track2.to_ytsearch_query.return_value = "Ed Sheeran Shape of You"

            with patch("mmpd.spotify_client.SpotifyClient.parse_url", return_value=[mock_track1, mock_track2]):
                from mmpd.spotify import parse_spotify_url_safe
                result = parse_spotify_url_safe("https://open.spotify.com/playlist/abc")

        assert len(result) == 2
        assert "Adele Hello" in result
        assert "Ed Sheeran Shape of You" in result

    def test_returns_empty_on_spotipy_error(self, monkeypatch):
        """Test return empty kalau spotipy raise exception."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()

            with patch("mmpd.spotify_client.SpotifyClient.parse_url", side_effect=Exception("API error")):
                from mmpd.spotify import parse_spotify_url_safe
                result = parse_spotify_url_safe("https://open.spotify.com/playlist/abc")
        assert result == []


# ============================================================================
# parse_spotify_url_v2 (return List[SpotifyTrack])
# ============================================================================

class TestParseSpotifyUrlV2:
    def test_non_spotify_url_returns_empty(self):
        """Test non-Spotify URL return empty list."""
        from mmpd.spotify import parse_spotify_url_v2
        result = parse_spotify_url_v2("https://youtube.com/watch?v=abc")
        assert result == []

    def test_returns_empty_without_credentials(self, monkeypatch):
        """Test return empty kalau spotipy tidak available."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        from mmpd import spotify_client as sc
        sc.reset_spotify_client()
        from mmpd.spotify import parse_spotify_url_v2
        result = parse_spotify_url_v2("https://open.spotify.com/playlist/abc")
        assert result == []

    def test_returns_tracks_with_spotipy(self, monkeypatch):
        """Test return List[SpotifyTrack] kalau spotipy berhasil parse."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        from mmpd.spotify_client import SpotifyTrack
        mock_tracks = [
            SpotifyTrack(title="Hello", artist="Adele", isrc="GBBKS1500214"),
            SpotifyTrack(title="Shape of You", artist="Ed Sheeran", isrc="GBAHS1500078"),
        ]

        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()

            with patch("mmpd.spotify_client.SpotifyClient.parse_url", return_value=mock_tracks):
                from mmpd.spotify import parse_spotify_url_v2
                result = parse_spotify_url_v2("https://open.spotify.com/playlist/abc")

        assert len(result) == 2
        assert result[0].title == "Hello"
        assert result[0].isrc == "GBBKS1500214"
        assert result[1].title == "Shape of You"

    def test_returns_empty_on_error(self, monkeypatch):
        """Test return empty kalau spotipy raise exception."""
        monkeypatch.setenv("SPOTIPY_CLIENT_ID", "test_id_1234567890")
        monkeypatch.setenv("SPOTIPY_CLIENT_SECRET", "test_secret_1234567890")

        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()

            with patch("mmpd.spotify_client.SpotifyClient.parse_url", side_effect=Exception("fail")):
                from mmpd.spotify import parse_spotify_url_v2
                result = parse_spotify_url_v2("https://open.spotify.com/playlist/abc")
        assert result == []
