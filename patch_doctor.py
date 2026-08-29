with open("mmpd/doctor.py", "r") as f:
    code = f.read()

old_logic = """    endpoints = [
        "lrclib.net",
        "itunes.apple.com",
        "api.spotify.com",
        "open.spotify.com",
        "www.youtube.com",
        "soundcloud.com",
    ]"""

new_logic = """    endpoints = [
        "lrclib.net",
        "itunes.apple.com",
        "api.spotify.com",
        "open.spotify.com",
        "www.youtube.com",
        "soundcloud.com",
        "music.163.com",
        "www.megalobiz.com",
        "translate.google.com",
        "api.mymemory.translated.net",
    ]"""

code = code.replace(old_logic, new_logic)
with open("mmpd/doctor.py", "w") as f:
    f.write(code)
