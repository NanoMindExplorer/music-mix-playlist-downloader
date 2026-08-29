with open("mmpd/spotify.py", "r") as f:
    code = f.read()

old_logic = """    # Menggunakan operator OR ('"audio" OR "official"') sering membingungkan YouTube 
    # dan malah memicu algoritma YouTube untuk mengembalikan versi Instrumental/Karaoke.
    # Solusi paling konsisten agar ADA SUARA PENYANYINYA adalah dengan 
    # menambahkan kata kunci "official audio" secara langsung.
    clean = f'{clean} official audio'
    return f"ytsearch{limit}:{clean}\""""

new_logic = """    # Fix instrumental: Gunakan exclusion filter yt-dlp / youtube
    clean = f'{clean} -instrumental -karaoke official audio'
    return f"ytsearch{limit}:{clean}\""""

code = code.replace(old_logic, new_logic)
with open("mmpd/spotify.py", "w") as f:
    f.write(code)
