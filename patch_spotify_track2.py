with open("mmpd/spotify_client.py", "r") as f:
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
with open("mmpd/spotify_client.py", "w") as f:
    f.write(code)
