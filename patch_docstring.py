with open("mmpd/spotify_client.py", "r") as f:
    code = f.read()

old_logic = "Kalau spotipy tidak terinstal ATAU env vars tidak ada, otomatis fallback ke legacy scraping via spotify_parser.py"
new_logic = "Kalau spotipy tidak terinstal ATAU env vars tidak ada, otomatis fallback ke metode embed scraping mandiri (_scrape_embed)."

code = code.replace(old_logic, new_logic)
with open("mmpd/spotify_client.py", "w") as f:
    f.write(code)
