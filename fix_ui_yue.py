with open("mmpd/ui.py", "r") as f:
    code = f.read()

old_list = """TRANSLITERATE_CHOICES: List[str] = [
    "❌ 1. Biarkan aslinya (Jangan ubah tulisan apapun)",
    "🇯🇵 2. Romaji (Ubah Kanji/Hiragana Jepang ke Alfabet)",
    "🇨🇳 3. Pinyin (Ubah Hanzi Mandarin ke Alfabet)",
    "🤖 4. Otomatis (Deteksi semua bahasa asing -> Alfabet)",
]"""

new_list = """TRANSLITERATE_CHOICES: List[str] = [
    "❌ 1. Biarkan aslinya (Jangan ubah tulisan apapun)",
    "🇯🇵 2. Romaji (Ubah Kanji/Hiragana Jepang ke Alfabet)",
    "🇨🇳 3. Pinyin (Ubah Hanzi Mandarin ke Alfabet)",
    "🇭🇰 4. Jyutping (Ubah Hanzi Kanton ke Alfabet)",
    "🤖 5. Otomatis (Deteksi semua bahasa asing -> Alfabet)",
]"""

code = code.replace(old_list, new_list)
with open("mmpd/ui.py", "w") as f:
    f.write(code)
