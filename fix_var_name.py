with open("mmpd/modes/download.py", "r") as f:
    code = f.read()

old_logic = """            selected_fmt = ask_select("Pilih Format Lirik Bilingual:", list(format_choices.keys()))
            if selected_fmt:
                os.environ["MMPD_BILINGUAL_FORMAT"] = format_choices[selected_fmt]"""

new_logic = """            selected_bilingual_fmt = ask_select("Pilih Format Lirik Bilingual:", list(format_choices.keys()))
            if selected_bilingual_fmt:
                os.environ["MMPD_BILINGUAL_FORMAT"] = format_choices[selected_bilingual_fmt]"""

code = code.replace(old_logic, new_logic)
with open("mmpd/modes/download.py", "w") as f:
    f.write(code)

with open("mmpd/modes/retrofit.py", "r") as f:
    code2 = f.read()

code2 = code2.replace(old_logic, new_logic)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code2)
