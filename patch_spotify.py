with open("tests/test_spotify.py", "r") as f:
    text = f.read()

text = text.replace(
    'assert "-instrumental" in result',
    'assert \'"audio" OR "official"\' in result'
)

with open("tests/test_spotify.py", "w") as f:
    f.write(text)
print("patched")
