import os
with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

old_logic = """def _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts):
    \"\"\"
    Tulis file LRC bilingual dengan format standar industri:
        [00:01.23] original text
        [00:01.23] terjemahan
    \"\"\"
    # Pastikan jumlah array cocok (MyMemory kadang potong baris kosong)
    if len(translated_texts) < len(lines):
        translated_texts.extend([""] * (len(lines) - len(translated_texts)))

    output = []
    for i, line in enumerate(lines):
        t_text = translated_texts[i].strip() if translated_texts[i] else ""
        if t_text and t_text.lower() != texts_to_translate[i].strip().lower():
            match = re.match(r"(\\[.*?\\])", line)
            if match:
                timestamp = match.group(1)
                original_text = line[len(timestamp):].rstrip("\\n")
                
                # Penalaran Maksimal (Update Komprehensif):
                # Trik spasi lebar (word-wrap) ternyata membuat beberapa pemutar musik gagal menggulir lirik (not scrolling)
                # karena baris dianggap terlalu panjang atau tidak valid.
                # Solusi paling ROBUST (anti-gagal) dan dijamin kompatibel dengan semua pemutar musik 
                # adalah menggabungkannya dalam 1 baris standar dengan pemisah tegas (garis miring / bullet).
                # Dengan ini:
                # 1. Lirik pasti digulir (scrolling normal).
                # 2. Lirik asli dan terjemahan disorot bersamaan.
                # 3. Lirik asli tetap berada di depan (prioritas).
                combined_line = f'{timestamp}{original_text}  /  {t_text}'
                output.append(combined_line)
            else:
                output.append(line.rstrip("\\n"))
        else:
            output.append(line.rstrip("\\n"))

    atomic_write_text(lrc_path, "\\n".join(output) + "\\n")"""

new_logic = """def _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts):
    \"\"\"
    Tulis file LRC bilingual dengan format standar industri atau gabungan.
    Konfigurasi format via ENV `MMPD_BILINGUAL_FORMAT` (gabung, pisah, id_only).
    \"\"\"
    format_mode = os.environ.get("MMPD_BILINGUAL_FORMAT", "gabung")

    if len(translated_texts) < len(lines):
        translated_texts.extend([""] * (len(lines) - len(translated_texts)))

    output = []
    output_id = []
    
    for i, line in enumerate(lines):
        t_text = translated_texts[i].strip() if translated_texts[i] else ""
        match = re.match(r"(\\[.*?\\])", line)
        
        if t_text and t_text.lower() != texts_to_translate[i].strip().lower() and match:
            timestamp = match.group(1)
            original_text = line[len(timestamp):].rstrip("\\n")
            
            if format_mode == "pisah":
                output.append(line.rstrip("\\n"))
                output.append(f'{timestamp}{t_text}')
            elif format_mode == "id_only":
                output.append(line.rstrip("\\n"))
                output_id.append(f'{timestamp}{t_text}')
            else:
                # Default: gabung
                combined_line = f'{timestamp}{original_text}  /  {t_text}'
                output.append(combined_line)
        else:
            output.append(line.rstrip("\\n"))
            if format_mode == "id_only" and match:
                output_id.append(line.rstrip("\\n"))

    if format_mode == "id_only":
        id_path = lrc_path.replace(".lrc", ".id.lrc")
        atomic_write_text(id_path, "\\n".join(output_id) + "\\n")
    
    atomic_write_text(lrc_path, "\\n".join(output) + "\\n")"""

code = code.replace(old_logic, new_logic)
with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
