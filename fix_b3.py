import re

with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

# Add detect_script helper
detect_helper = """_HIRAGANA_KATAKANA = re.compile(r'[\u3040-\u30ff]')
_HAN = re.compile(r'[\u4e00-\u9fff]')
_HANGUL = re.compile(r'[\uac00-\ud7a3]')
_THAI = re.compile(r'[\u0e00-\u0e7f]')

def detect_script(text: str) -> str:
    if _HIRAGANA_KATAKANA.search(text): return "ja"
    if _HANGUL.search(text): return "ko"
    if _HAN.search(text): return "zh"
    if _THAI.search(text): return "th"
    return "latin"

"""

# We need to inject this somewhere around line 70
if "def detect_script" not in code:
    code = code.replace("def _transliterate_japanese", detect_helper + "def _transliterate_japanese")

with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
