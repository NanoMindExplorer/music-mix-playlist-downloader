with open("mmpd/modes/retrofit.py", "r") as f:
    code = f.read()

old_logic = """    if (
        lyrics_mode.startswith("🎧 1") or lyrics_mode.startswith("✍️ 2")
    ) and not os.path.exists(lrc_path) and not (sync_huawei and os.path.exists(huawei_lrc_path)):
        query = None
        if lyrics_mode.startswith("✍️ 2"):
            progress.stop()
            query = ask_text(f"📝 Masukkan judul Spotify untuk '{title}':")
            progress.start()
        fetch_synced_lyrics(
            title=title,
            lrc_path=lrc_path,
            sync_huawei=sync_huawei,
            transliterate_mode=transliterate,
            override_query=query,
            translate_mode=translate_id,
        )"""

new_logic = """    if (lyrics_mode.startswith("🎧 1") or lyrics_mode.startswith("✍️ 2")) and not os.path.exists(lrc_path):
        if sync_huawei and os.path.exists(huawei_lrc_path):
            shutil.copy2(huawei_lrc_path, lrc_path)
        else:
            query = None
            if lyrics_mode.startswith("✍️ 2"):
                progress.stop()
                query = ask_text(f"📝 Masukkan judul Spotify untuk '{title}':")
                progress.start()
            fetch_synced_lyrics(
                title=title,
                lrc_path=lrc_path,
                sync_huawei=sync_huawei,
                transliterate_mode=transliterate,
                override_query=query,
                translate_mode=translate_id,
            )"""

code = code.replace(old_logic, new_logic)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code)
