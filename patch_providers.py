with open("tests/test_lyrics_providers.py", "r") as f:
    text = f.read()

text = text.replace(
    'assert chain._providers[1].name == "syncedlyrics"',
    'assert chain._providers[1].name == "musixmatch_native"\n        assert chain._providers[2].name == "syncedlyrics"'
)

with open("tests/test_lyrics_providers.py", "w") as f:
    f.write(text)
print("patched")
