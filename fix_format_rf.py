with open("mmpd/modes/retrofit.py", "r") as f:
    code = f.read()

old_logic = """    translate_id = False
    if not (lyrics_mode.startswith("❌ 4") or lyrics_mode.startswith("📺 3")):
        transliterate = ask_select(
            "Pilih Mode Transliterasi (Ubah huruf asing ke Alfabet):",
            TRANSLITERATE_CHOICES,
        )
        if not transliterate:
            return
        translate_id = ask_confirm(
            "Terjemahkan Lirik Asing ke Bahasa Indonesia (Bilingual)?", default=True
        )"""

new_logic = """    translate_id = False
    if not (lyrics_mode.startswith("❌ 4") or lyrics_mode.startswith("📺 3")):
        transliterate = ask_select(
            "Pilih Mode Transliterasi (Ubah huruf asing ke Alfabet):",
            TRANSLITERATE_CHOICES,
        )
        if not transliterate:
            return
        translate_id = ask_confirm(
            "Terjemahkan Lirik Asing ke Bahasa Indonesia (Bilingual)?", default=True
        )
        if translate_id:
            format_choices = {
                "🔤 1. Gabung 1 baris (Teraman, Default)": "gabung",
                "⏱️ 2. Pisah 2 baris (Micro-offset) - Terbaik untuk Poweramp": "pisah",
                "📁 3. File terpisah (.id.lrc)": "id_only"
            }
            selected_fmt = ask_select("Pilih Format Lirik Bilingual:", list(format_choices.keys()))
            if selected_fmt:
                import os
                os.environ["MMPD_BILINGUAL_FORMAT"] = format_choices[selected_fmt]"""

code = code.replace(old_logic, new_logic)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code)
