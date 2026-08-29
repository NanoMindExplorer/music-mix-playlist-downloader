with open("mmpd/types.py", "r") as f:
    code = f.read()

new_logic = """@dataclass(frozen=True)
class SpotifyTrack:
    \"\"\"
    Spotify track metadata (lebih lengkap dari TrackInfo biasa).

    Field tambahan vs TrackInfo:
        - isrc:          International Standard Recording Code (untuk YouTube matching akurat)
        - spotify_url:   URL Spotify asli (untuk debugging)
        - popularity:    0-100 score dari Spotify (untuk disambiguation)
        - explicit:      True kalau lagu explicit
        - cover_url:     URL gambar cover art dari Spotify
    \"\"\"

    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    spotify_url: Optional[str] = None
    popularity: Optional[int] = None
    explicit: bool = False
    cover_url: Optional[str] = None"""

old_logic = """@dataclass(frozen=True)
class SpotifyTrack:
    \"\"\"
    Spotify track metadata (lebih lengkap dari TrackInfo biasa).

    Field tambahan vs TrackInfo:
        - isrc:          International Standard Recording Code (untuk YouTube matching akurat)
        - spotify_url:   URL Spotify asli (untuk debugging)
        - popularity:    0-100 score dari Spotify (untuk disambiguation)
        - explicit:      True kalau lagu explicit
    \"\"\"

    title: str
    artist: str
    album: Optional[str] = None
    duration_ms: Optional[int] = None
    isrc: Optional[str] = None
    spotify_url: Optional[str] = None
    popularity: Optional[int] = None
    explicit: bool = False"""

code = code.replace(old_logic, new_logic)
with open("mmpd/types.py", "w") as f:
    f.write(code)

with open("mmpd/spotify_client.py", "r") as f:
    code2 = f.read()

old_logic_resp = """        return SpotifyTrack(
            title=title,
            artist=artist_str,
            album=album_name,
            duration_ms=data.get("duration_ms"),
            isrc=isrc,
            spotify_url=data.get("external_urls", {}).get("spotify"),
            popularity=data.get("popularity"),
            explicit=data.get("explicit", False),
        )"""

new_logic_resp = """        # Gambar cover
        cover_url = None
        images = album_data.get("images", [])
        if images and isinstance(images, list):
            cover_url = images[0].get("url")

        return SpotifyTrack(
            title=title,
            artist=artist_str,
            album=album_name,
            duration_ms=data.get("duration_ms"),
            isrc=isrc,
            spotify_url=data.get("external_urls", {}).get("spotify"),
            popularity=data.get("popularity"),
            explicit=data.get("explicit", False),
            cover_url=cover_url,
        )"""

old_logic_embed1 = """                    if title:
                        tracks.append(SpotifyTrack(title=title, artist=artist, spotify_url=item.get("uri", "")))"""
new_logic_embed1 = """                    if title:
                        cover_url = entity.get("coverArt", {}).get("sources", [{}])[0].get("url")
                        if not cover_url:
                            cover_url = item.get("coverArt", {}).get("sources", [{}])[0].get("url")
                        tracks.append(SpotifyTrack(title=title, artist=artist, spotify_url=item.get("uri", ""), cover_url=cover_url))"""

old_logic_embed2 = """                    tracks.append(SpotifyTrack(title=title, artist=artist, spotify_url=entity.get("uri", "")))"""
new_logic_embed2 = """                    cover_url = entity.get("coverArt", {}).get("sources", [{}])[0].get("url")
                    tracks.append(SpotifyTrack(title=title, artist=artist, spotify_url=entity.get("uri", ""), cover_url=cover_url))"""

code2 = code2.replace(old_logic_resp, new_logic_resp)
code2 = code2.replace(old_logic_embed1, new_logic_embed1)
code2 = code2.replace(old_logic_embed2, new_logic_embed2)
with open("mmpd/spotify_client.py", "w") as f:
    f.write(code2)
