"""
Unit tests untuk mmpd.spotify — parse_spotify_url_safe + parse_spotify_url_v2 + fallback chain.

Strategy:
    - Mock spotify_client.get_spotify_client untuk test fallback ke legacy
    - Mock spotify_parser.parse_spotify_url untuk test legacy fallback
    - Test is_spotify_url validator
    - Test build_ytsearch_query
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
        # "spotify.com" tanpa "open" → False
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
        # Bracket dan "Official" harus hilang
        assert "ytsearch1:" in result
        assert "[" not in result
        assert "(" not in result

    def test_empty_query_after_clean(self):
        """Test empty query setelah clean pakai original."""
        from mmpd.spotify import build_ytsearch_query
        result = build_ytsearch_query("[Official]", limit=1)
        # Setelah clean, empty → pakai original stripped
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

        # Mock spotipy module
        mock_spotipy = MagicMock()
        with patch.dict("sys.modules", {"spotipy": mock_spotipy}):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()
            from mmpd.spotify import spotipy_available
            assert spotipy_available() is True


# ============================================================================
# parse_spotify_url_safe (backward compat, return List[str])
# ============================================================================

class TestParseSpotifyUrlSafe:
    def test_non_spotify_url_returns_empty(self):
        """Test non-Spotify URL return empty list."""
        from mmpd.spotify import parse_spotify_url_safe
        result = parse_spotify_url_safe("https://youtube.com/watch?v=abc")
        assert result == []

    def test_fallback_to_legacy_scraping(self, monkeypatch):
        """Test fallback ke legacy scraping kalau spotipy tidak available."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        # Mock legacy parser
        mock_legacy_result = ["Adele Hello", "Ed Sheeran Shape of You"]
        with patch("spotify_parser.parse_spotify_url", return_value=mock_legacy_result):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()
            from mmpd.spotify import parse_spotify_url_safe
            result = parse_spotify_url_safe("https://open.spotify.com/playlist/abc")
        assert result == mock_legacy_result

    def test_legacy_returns_empty_on_failure(self, monkeypatch):
        """Test legacy scraping return empty kalau gagal."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        with patch("spotify_parser.parse_spotify_url", return_value=[]):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()
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

    def test_fallback_to_legacy_returns_spotify_tracks(self, monkeypatch):
        """Test fallback ke legacy, wrap ke SpotifyTrack."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        mock_legacy_result = ["Adele Hello", "Ed Sheeran Shape of You"]
        with patch("spotify_parser.parse_spotify_url", return_value=mock_legacy_result):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()
            from mmpd.spotify import parse_spotify_url_v2
            result = parse_spotify_url_v2("https://open.spotify.com/playlist/abc")

        # Should return list of SpotifyTrack (without ISRC since legacy)
        assert len(result) == 2
        # SpotifyTrack should have title and artist attributes
        for track in result:
            assert hasattr(track, "title")
            assert hasattr(track, "artist")
            assert track.isrc is None  # Legacy tidak punya ISRC

    def test_legacy_empty_returns_empty(self, monkeypatch):
        """Test legacy scraping empty return empty list."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        with patch("spotify_parser.parse_spotify_url", return_value=[]):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()
            from mmpd.spotify import parse_spotify_url_v2
            result = parse_spotify_url_v2("https://open.spotify.com/playlist/abc")
        assert result == []


# ============================================================================
# SpotifyTrack conversion (via v2 fallback)
# ============================================================================

class TestSpotifyTrackConversion:
    def test_legacy_query_split_correctly(self, monkeypatch):
        """Test legacy "Artist Title" string di-split jadi artist + title."""
        monkeypatch.delenv("SPOTIPY_CLIENT_ID", raising=False)
        monkeypatch.delenv("SPOTIPY_CLIENT_SECRET", raising=False)

        # Legacy return "Adele Hello" → artist="Adele", title="Hello"
        mock_legacy_result = ["Adele Hello"]
        with patch("spotify_parser.parse_spotify_url", return_value=mock_legacy_result):
            from mmpd import spotify_client as sc
            sc.reset_spotify_client()
            from mmpd.spotify import parse_spotify_url_v2
            result = parse_spotify_url_v2("https://open.spotify.com/track/abc")

        assert len(result) == 1
        track = result[0]
        # Heuristik: split di spasi pertama → artist="Adele", title="Hello"
        assert track.artist == "Adele"
        assert track.title == "Hello"
