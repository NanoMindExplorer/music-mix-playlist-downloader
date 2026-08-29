import re

with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

old_block = """        # Tentukan bahasa target
        target_lang = ""
        if transliterate_mode.startswith("🤖 4"):
            import langdetect
            try:
                target_lang = langdetect.detect(pure_text)
            except Exception:
                _log.warning("langdetect gagal, skip transliterasi")
                return

            if target_lang in _LATIN_LANGUAGES:
                _log.debug("Bahasa %s sudah Latin, skip transliterasi", target_lang)
                return
        elif transliterate_mode.startswith("🇯🇵 2"):
            target_lang = "ja"
        elif transliterate_mode.startswith("🇨🇳 3"):
            target_lang = "zh-cn"

        # Pilih transliterator sesuai bahasa
        if target_lang == "ja":
            new_lines = _transliterate_japanese(lines)
        elif target_lang in ("zh-cn", "zh-tw"):
            new_lines = _transliterate_chinese(lines)
        elif target_lang == "ko":
            new_lines = _transliterate_korean(lines)
        else:
            new_lines = _transliterate_universal(lines)"""

new_block = """        # Init engines lazily
        engines = {}

        def _get_kakasi():
            if "ja" not in engines:
                from pykakasi import kakasi
                engines["ja"] = kakasi()
            return engines["ja"]

        def _get_pinyin():
            if "zh" not in engines:
                from pypinyin import pinyin, Style
                engines["zh"] = (pinyin, Style)
            return engines["zh"]

        def _get_korean():
            if "ko" not in engines:
                from korean_romanizer.romanizer import Romanizer
                engines["ko"] = Romanizer
            return engines["ko"]
            
        def _get_anyascii():
            if "anyascii" not in engines:
                from anyascii import anyascii
                engines["anyascii"] = anyascii
            return engines["anyascii"]

        def _trans_line(line: str, lang: str) -> str:
            text = re.sub(r"\\[.*?\\]", "", line).strip()
            if not text: return line
            time_tags = "".join(re.findall(r"\\[.*?\\]", line))
            
            try:
                if lang == "ja":
                    k = _get_kakasi()
                    conv = k.convert(text)
                    new_text = "".join([item["hepburn"] for item in conv])
                    return f"{time_tags}{new_text}\\n"
                elif lang in ("zh", "zh-cn", "zh-tw"):
                    pinyin, Style = _get_pinyin()
                    py_list = pinyin(text, style=Style.NORMAL)
                    new_text = " ".join([item[0] for item in py_list])
                    return f"{time_tags}{new_text}\\n"
                elif lang == "ko":
                    Romanizer = _get_korean()
                    new_text = Romanizer(text).romanize()
                    return f"{time_tags}{new_text}\\n"
                elif lang == "th":
                    anyascii = _get_anyascii()
                    new_text = anyascii(text)
                    return f"{time_tags}{new_text}\\n"
            except Exception as e:
                _log.warning("Transliterator error: %s", e)
            return line

        new_lines = []
        target_lang = "auto"
        if transliterate_mode.startswith("🤖 4"):
            for line in lines:
                text = re.sub(r"\\[.*?\\]", "", line).strip()
                if not text:
                    new_lines.append(line)
                    continue
                lang = detect_script(text)
                if lang == "latin":
                    new_lines.append(line)
                else:
                    new_lines.append(_trans_line(line, lang))
        else:
            if transliterate_mode.startswith("🇯🇵 2"):
                target_lang = "ja"
            elif transliterate_mode.startswith("🇨🇳 3"):
                target_lang = "zh"
            else:
                target_lang = "latin"
            
            for line in lines:
                new_lines.append(_trans_line(line, target_lang))"""

if old_block in code:
    code = code.replace(old_block, new_block)
    with open("mmpd/lyrics.py", "w") as f:
        f.write(code)
    print("Replaced!")
else:
    print("Old block not found!")
