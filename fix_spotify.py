with open("tests/test_spotify.py", "r") as f:
    text = f.read()

text = text.replace('        def test_query_with_limit_3', '\n    def test_query_with_limit_3')

with open("tests/test_spotify.py", "w") as f:
    f.write(text)
print("fixed")
