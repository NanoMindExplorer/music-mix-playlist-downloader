with open("mmpd/modes/download.py", "r") as f:
    code = f.read()

old_logic = """        translate_id = ask_confirm(
            "🌐 Terjemahkan Lirik ke Bahasa Indonesia (Otomatis ditambahkan di bawah teks asli)?",
            default=True,
        )"""

new_logic = """        translate_id = ask_confirm(
            "🌐 Terjemahkan Lirik ke Bahasa Indonesia (Otomatis ditambahkan di bawah teks asli)?",
            default=True,
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
with open("mmpd/modes/download.py", "w") as f:
    f.write(code)
