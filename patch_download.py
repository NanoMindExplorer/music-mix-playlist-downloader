with open("mmpd/modes/download.py", "r") as f:
    code = f.read()

old_logic = """            elif os.path.exists(lrc_path):
                # Lirik sudah ada (dari YouTube CC) — apply post-processing
                process_transliteration(lrc_path, transliterate)
                process_translation(lrc_path, translate_id)"""

new_logic = """            elif os.path.exists(lrc_path):
                # Lirik sudah ada (dari YouTube CC) — apply post-processing
                source_lines = None
                try:
                    with open(lrc_path, "r", encoding="utf-8") as f:
                        source_lines = f.readlines()
                except Exception:
                    pass
                process_transliteration(lrc_path, transliterate)
                process_translation(lrc_path, translate_id, source_lines=source_lines)"""

code = code.replace(old_logic, new_logic)
with open("mmpd/modes/download.py", "w") as f:
    f.write(code)
