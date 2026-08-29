with open("tests/test_spotify_client.py", "r") as f:
    code = f.read()

old_logic = """                                        {"title": "Song 1", "subtitle": "Artist 1", "uri": "spotify:track:1"}"""

new_logic = """                                        {"title": "Song 1", "subtitle": "Artist 1", "uri": "spotify:track:1", "coverArt": {"sources": [{"url": "http://img"}]}}"""

code = code.replace(old_logic, new_logic)
with open("tests/test_spotify_client.py", "w") as f:
    f.write(code)
