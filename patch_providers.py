import re

with open("mmpd/lyrics_providers.py", "r") as f:
    code = f.read()

new_logic = """def build_default_chain(title: str = "") -> LyricsChain:
    \"\"\"
    B4: Urutan dinamis berdasarkan script judul (NetEase diutamakan untuk CJK/Thai).
    \"\"\"
    from mmpd.lyrics import detect_script
    script = detect_script(title) if title else "latin"
    
    # Default: Barat/Latin
    chain = [MusixmatchProvider(), LrclibProvider(), SyncedLyricsProvider()]
    
    if script in ("ja", "zh", "ko", "th"):
        # Untuk CJK & Thai, SyncedLyricsProvider (NetEase/Megalobiz) punya katalog lebih baik
        chain = [SyncedLyricsProvider(), MusixmatchProvider(), LrclibProvider()]
        
    return LyricsChain(chain)"""

old_logic = """def build_default_chain(title: str = "") -> LyricsChain:
    \"\"\"
    Urutan provider tahan timeout:
        1. Musixmatch native (paling cocok lagu Asia + pilihan UI "Spotify/Musixmatch")
        2. LRCLIB (gratis, jarang timeout)
        3. syncedlyrics (NetEase/Megalobiz) sebagai fallback terakhir
    \"\"\"
    return LyricsChain([MusixmatchProvider(), LrclibProvider(), SyncedLyricsProvider()])"""

code = code.replace(old_logic, new_logic)
with open("mmpd/lyrics_providers.py", "w") as f:
    f.write(code)
