import re

with open("mmpd/lyrics_providers.py", "r") as f:
    content = f.read()

musixmatch_code = """
# ============================================================================
# Provider 2: Musixmatch Native (Bypass syncedlyrics)
# ============================================================================

class MusixmatchProvider:
    \"\"\"
    Native Musixmatch Provider menggunakan Desktop API.
    Lebih stabil daripada wrapper syncedlyrics karena kita handle
    token generation dan macro.subtitles.get secara langsung,
    dan langsung bypass limitasi.
    \"\"\"

    name = "musixmatch_native"
    priority = 5

    BASE_URL = "https://apic-desktop.musixmatch.com/ws/1.1"
    APP_ID = "web-desktop-app-v1.0"
    REQUEST_TIMEOUT = (10, 30)

    def __init__(self) -> None:
        self._user_token = None
        self._token_time = 0

    def _get_token(self, requests_module) -> Optional[str]:
        import time
        # Cache token for 10 minutes
        if self._user_token and (time.time() - self._token_time) < 600:
            return self._user_token

        try:
            url = f"{self.BASE_URL}/token.get?app_id={self.APP_ID}"
            res = requests_module.get(url, timeout=self.REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
            res.raise_for_status()
            data = res.json()
            token = data.get("message", {}).get("body", {}).get("user_token")
            if token:
                self._user_token = token
                self._token_time = time.time()
                return token
        except Exception as e:
            get_logger().warning("Musixmatch token generation failed: %s", e)
        return None

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        log = get_logger()
        try:
            import requests
        except ImportError:
            return None

        token = self._get_token(requests)
        if not token:
            return None

        # Build query
        params = {
            "format": "json",
            "app_id": self.APP_ID,
            "usertoken": token,
        }
        
        if track.isrc:
            params["track_isrc"] = track.isrc
        else:
            params["q_track"] = track.title
            if track.artist:
                params["q_artist"] = track.artist

        log.debug("Musixmatch search: query='%s', isrc=%s", track.search_query(), track.isrc)

        try:
            url = f"{self.BASE_URL}/macro.subtitles.get"
            res = requests.get(url, params=params, timeout=self.REQUEST_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
            res.raise_for_status()
            data = res.json()

            macro_calls = data.get("message", {}).get("body", {}).get("macro_calls", {})
            subtitles_list = macro_calls.get("track.subtitles.get", {}).get("message", {}).get("body", {}).get("subtitle_list", [])
            
            if not subtitles_list:
                log.debug("Musixmatch: no subtitles found for '%s'", track.title)
                return None
                
            synced_lyrics = subtitles_list[0].get("subtitle", {}).get("subtitle_body", "")
            if not synced_lyrics:
                return None

            # Get track metadata
            track_meta = macro_calls.get("matcher.track.get", {}).get("message", {}).get("body", {}).get("track", {})
            track_name = track_meta.get("track_name", track.title)
            artist_name = track_meta.get("artist_name", track.artist)

            log.info("Musixmatch: match for '%s'", track_name)
            return LyricsResult(
                synced_lyrics=synced_lyrics,
                plain_lyrics=None,
                provider="musixmatch",
                track_name=track_name,
                artist_name=artist_name,
            )

        except Exception as e:
            log.warning("Musixmatch API failed for '%s': %s", track.title, e)
            return None

# ============================================================================
# Provider 3: syncedlyrics (wrapper library lama, tetap dipertahankan)
# ============================================================================
"""

content = content.replace(
"""# ============================================================================
# Provider 2: syncedlyrics (wrapper library lama, tetap dipertahankan)
# ============================================================================""", musixmatch_code)

content = content.replace(
    'lrc_text = self._search_fn(clean_query)',
    'lrc_text = self._search_fn(clean_query, providers=["NetEase", "Megalobiz"])'
)
content = content.replace(
    'lrc_text = self._search_fn(raw_query)',
    'lrc_text = self._search_fn(raw_query, providers=["NetEase", "Megalobiz"])'
)

# Also update build_default_chain
chain_code = """    return LyricsChain([
        LrclibProvider(),
        MusixmatchProvider(),
        SyncedLyricsProvider(),
    ])"""
content = re.sub(r'    return LyricsChain\(\[.*?\]\)', chain_code, content, flags=re.DOTALL)

with open("mmpd/lyrics_providers.py", "w") as f:
    f.write(content)
print("patched")
