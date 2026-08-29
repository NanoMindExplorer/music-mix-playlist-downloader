with open("mmpd/lyrics_providers.py", "r") as f:
    code = f.read()

old_func = """def build_default_chain() -> LyricsChain:
    \"\"\"
    Build default lyrics chain: LRCLIB → syncedlyrics.

    Future providers (Musixmatch, NetEase direct, YoutubeCC) bisa ditambahkan
    di sini tanpa modif caller code.
    \"\"\"
    return LyricsChain([
        LrclibProvider(),
        MusixmatchProvider(),
        SyncedLyricsProvider(),
    ])"""

new_func = """def build_default_chain(title: str = "") -> LyricsChain:
    from mmpd.lyrics import detect_script
    script = detect_script(title) if title else "latin"
    if script in ("ja", "zh", "ko", "th"):
        return LyricsChain([SyncedLyricsProvider(), MusixmatchProvider(), LrclibProvider()])
    return LyricsChain([LrclibProvider(), MusixmatchProvider(), SyncedLyricsProvider()])"""

code = code.replace(old_func, new_func)
with open("mmpd/lyrics_providers.py", "w") as f:
    f.write(code)
