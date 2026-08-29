with open("mmpd/lyrics_providers.py", "r") as f:
    code = f.read()

new_logic = """_PROVIDER_FAILS = {}

    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        \"\"\"Cari lirik via syncedlyrics. Return None jika tidak ditemukan.\"\"\"
        log = get_logger()
        if not self._ensure_initialized():
            return None

        clean_query = track.clean_search_query()
        log.debug("syncedlyrics search: query='%s'", clean_query)

        global _PROVIDER_FAILS
        try:
            lrc_text = None
            for p in (["Musixmatch"], ["NetEase"], ["Megalobiz"]):
                provider_name = p[0]
                if _PROVIDER_FAILS.get(provider_name, 0) >= 3:
                    log.info("⏭️ %s dilewati untuk sisa sesi ini (gagal 3x berturut)", provider_name)
                    continue
                    
                try:
                    lrc_text = self._search_fn(clean_query, providers=p)
                    if lrc_text:
                        _PROVIDER_FAILS[provider_name] = 0  # reset on success
                        break
                except Exception as e:
                    _PROVIDER_FAILS[provider_name] = _PROVIDER_FAILS.get(provider_name, 0) + 1
                    log.warning("syncedlyrics %s gagal: %s", p, e)
                    lrc_text = None
"""
old_logic = """    def search(self, track: TrackInfo) -> Optional[LyricsResult]:
        \"\"\"Cari lirik via syncedlyrics. Return None jika tidak ditemukan.\"\"\"
        log = get_logger()
        if not self._ensure_initialized():
            return None

        # Coba pakai clean query dulu (lebih akurat)
        clean_query = track.clean_search_query()
        log.debug("syncedlyrics search: query='%s'", clean_query)

        try:
            # Musixmatch dulu (pilihan user "Mesin Spotify/Musixmatch"),
            # NetEase/Megalobiz sering timeout di Termux.
            lrc_text = None
            for providers in (
                ["Musixmatch"],
                ["NetEase"],
                ["Megalobiz"],
            ):
                try:
                    lrc_text = self._search_fn(clean_query, providers=providers)
                except Exception as e:
                    log.warning("syncedlyrics %s gagal: %s", providers, e)
                    lrc_text = None
                if lrc_text:
                    break"""

code = code.replace(old_logic, new_logic)
with open("mmpd/lyrics_providers.py", "w") as f:
    f.write(code)
