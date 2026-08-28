import pytest
from unittest.mock import patch, MagicMock
from mmpd.cover_providers import get_cover_art_url, download_cover_art

@patch("mmpd.cover_providers.requests.get")
def test_get_cover_art_url_itunes(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "resultCount": 1,
        "results": [{"artworkUrl100": "http://example.com/100x100bb.jpg"}]
    }
    mock_get.return_value = mock_resp
    
    url = get_cover_art_url("Never Gonna Give You Up", "Rick Astley")
    assert url == "http://example.com/3000x3000bb.jpg"

@patch("mmpd.cover_providers.requests.get")
def test_get_cover_art_url_deezer(mock_get):
    # Simulate iTunes fail, Deezer success
    mock_itunes = MagicMock()
    mock_itunes.status_code = 404
    
    mock_deezer = MagicMock()
    mock_deezer.status_code = 200
    mock_deezer.json.return_value = {
        "data": [{"album": {"cover_xl": "http://deezer.com/cover.jpg"}}]
    }
    
    # We also mock MusicBrainz since it is between iTunes and Deezer
    mock_mb = MagicMock()
    mock_mb.status_code = 404
    
    mock_get.side_effect = [mock_itunes, mock_mb, mock_deezer]
    
    url = get_cover_art_url("Song", "Artist")
    assert url == "http://deezer.com/cover.jpg"

@patch("mmpd.cover_providers.requests.get")
def test_download_cover_art(mock_get, tmp_path):
    mock_resp_api = MagicMock()
    mock_resp_api.status_code = 200
    mock_resp_api.json.return_value = {
        "resultCount": 1,
        "results": [{"artworkUrl100": "http://example.com/100x100bb.jpg"}]
    }
    
    mock_resp_img = MagicMock()
    mock_resp_img.status_code = 200
    mock_resp_img.content = b"fake_image_data"
    
    mock_get.side_effect = [mock_resp_api, mock_resp_img]
    
    out_path = tmp_path / "cover.jpg"
    assert download_cover_art("Test", "Artist", str(out_path)) == True
    assert out_path.read_bytes() == b"fake_image_data"

def test_download_cover_art_fail():
    with patch("mmpd.cover_providers.get_cover_art_url", return_value=None):
        assert download_cover_art("Test", "Artist", "out.jpg") == False
