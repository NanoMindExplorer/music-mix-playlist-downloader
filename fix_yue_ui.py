with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

old_logic = """        else:
            if transliterate_mode.startswith("🇯🇵 2"):
                target_lang = "ja"
            elif transliterate_mode.startswith("🇨🇳 3"):
                target_lang = "zh"
            else:
                target_lang = "latin"
            
            for line in lines:
                new_lines.append(_trans_line(line, target_lang))"""

new_logic = """        else:
            if transliterate_mode.startswith("🇯🇵 2"):
                target_lang = "ja"
            elif transliterate_mode.startswith("🇨🇳 3"):
                target_lang = "zh"
            elif "Kanton" in transliterate_mode or transliterate_mode.startswith("🇭🇰"):
                target_lang = "yue"
            else:
                target_lang = "latin"
            
            for line in lines:
                new_lines.append(_trans_line(line, target_lang))"""

code = code.replace(old_logic, new_logic)
with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
