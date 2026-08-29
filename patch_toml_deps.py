with open("pyproject.toml", "r") as f:
    code = f.read()

code = code.replace(
    '"spotipy>=2.23.0",\n]',
    '"spotipy>=2.23.0",\n    "opencc-python-reimplemented>=0.1.7",\n    "ToJyutping>=0.2.1",\n    "pythainlp>=4.0.0",\n]'
)
with open("pyproject.toml", "w") as f:
    f.write(code)
