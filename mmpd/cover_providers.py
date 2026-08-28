import os
import requests
from typing import Optional
from mmpd.logger import get_logger

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    _HAS_SPOTIPY = True
except ImportError:
    _HAS_SPOTIPY = False

_log = get_logger()

def get_cover_art_url(title: str, artist: str = "") -> Optional[str]:
    query = f"{title} {artist}".strip()
    
    # 1. iTunes
    try:
        res = requests.get("https://itunes.apple.com/search", params={"term": query, "media": "music", "entity": "song", "limit": 1}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("resultCount", 0) > 0:
                url = data["results"][0].get("artworkUrl100")
                if url:
                    return url.replace("100x100bb", "3000x3000bb")
    except Exception as e:
        _log.warning("iTunes search failed: %s", e)

    # 2. Spotify
    if _HAS_SPOTIPY and os.environ.get("SPOTIPY_CLIENT_ID") and os.environ.get("SPOTIPY_CLIENT_SECRET"):
        try:
            sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
            results = sp.search(q=query, type='track', limit=1)
            if results and results.get('tracks', {}).get('items'):
                track = results['tracks']['items'][0]
                if track.get('album', {}).get('images'):
                    return track['album']['images'][0]['url']
        except Exception as e:
            _log.warning("Spotify search failed: %s", e)

    # 3. MusicBrainz
    try:
        res = requests.get("https://musicbrainz.org/ws/2/recording", params={"query": query, "fmt": "json", "limit": 1}, headers={"User-Agent": "MMPD/1.0"}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("recordings") and len(data["recordings"]) > 0:
                release_id = data["recordings"][0].get("releases", [{}])[0].get("id")
                if release_id:
                    c_res = requests.get(f"https://coverartarchive.org/release/{release_id}")
                    if c_res.status_code == 200:
                        images = c_res.json().get("images", [])
                        if images:
                            return images[0].get("image")
    except Exception as e:
        _log.warning("MusicBrainz search failed: %s", e)

    # 4. Deezer
    try:
        res = requests.get("https://api.deezer.com/search", params={"q": query, "limit": 1}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0].get("album", {}).get("cover_xl")
    except Exception as e:
        _log.warning("Deezer search failed: %s", e)

    return None

def download_cover_art(title: str, artist: str, output_path: str) -> bool:
    url = get_cover_art_url(title, artist)
    if not url: return False
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(res.content)
        return True
    except Exception:
        return False
