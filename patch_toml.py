with open("pyproject.toml", "r") as f:
    code = f.read()

# H: Remove spotify_parser
code = code.replace('"downloader", "spotify_parser"', '"downloader"')

# H2: Sync dependencies
old_deps = '''dependencies = [
    "rich>=13.7.0",
    "yt-dlp>=2023.12.30",
    "mutagen>=1.47.0",
    "requests>=2.31.0",
    "colorama>=0.4.6",
    "inquirer>=3.2.4",
    "syncedlyrics>=0.33.0",
    "deep-translator>=1.11.4",
    "langdetect>=1.0.9",
    "pykakasi>=2.2.8",
    "pypinyin>=0.51.0",
    "hangul-romanize>=0.1.0",
    "spotipy>=2.23.0"
]'''

new_deps = '''dependencies = [
    "rich>=13.7.0",
    "yt-dlp>=2023.12.30",
    "mutagen>=1.47.0",
    "requests>=2.31.0",
    "colorama>=0.4.6",
    "inquirer>=3.2.4",
    "syncedlyrics>=0.33.0",
    "deep-translator>=1.11.4",
    "langdetect>=1.0.9",
    "pykakasi>=2.2.8",
    "pypinyin>=0.51.0",
    "hangul-romanize>=0.1.0",
    "spotipy>=2.23.0",
    "opencc-python-reimplemented>=0.1.7",
    "ToJyutping>=0.2.1",
    "pythainlp>=4.0.0"
]'''
code = code.replace(old_deps, new_deps)
with open("pyproject.toml", "w") as f:
    f.write(code)
