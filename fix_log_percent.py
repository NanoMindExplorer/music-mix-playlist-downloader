with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

code = code.replace(
    '_log.info("Translation: 100% cache hit',
    '_log.info("Translation: 100%% cache hit'
)

with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
