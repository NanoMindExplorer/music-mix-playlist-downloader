with open("mmpd/modes/retrofit.py", "r") as f:
    code = f.read()

old_logic1 = """            process_transliteration(new_path, transliterate)
            process_translation(new_path, translate_id)"""

new_logic1 = """            orig_lines = None
            try:
                with open(new_path, "r", encoding="utf-8") as f:
                    orig_lines = f.readlines()
            except Exception:
                pass
            process_transliteration(new_path, transliterate)
            process_translation(new_path, translate_id, source_lines=orig_lines)"""

old_logic2 = """            process_transliteration(lrc_file, transliterate)
            process_translation(lrc_file, translate_id)"""

new_logic2 = """            orig_lines = None
            try:
                with open(lrc_file, "r", encoding="utf-8") as f:
                    orig_lines = f.readlines()
            except Exception:
                pass
            process_transliteration(lrc_file, transliterate)
            process_translation(lrc_file, translate_id, source_lines=orig_lines)"""

old_logic3 = """        shutil.move(backup_lrc, lrc_path)
        _log.info("Restore LRC backup (fetch gagal): %s", os.path.basename(lrc_path))
        process_transliteration(lrc_path, transliterate)
        process_translation(lrc_path, translate_id)"""

new_logic3 = """        shutil.move(backup_lrc, lrc_path)
        _log.info("Restore LRC backup (fetch gagal): %s", os.path.basename(lrc_path))
        orig_lines = None
        try:
            with open(lrc_path, "r", encoding="utf-8") as f:
                orig_lines = f.readlines()
        except Exception:
            pass
        process_transliteration(lrc_path, transliterate)
        process_translation(lrc_path, translate_id, source_lines=orig_lines)"""

code = code.replace(old_logic1, new_logic1).replace(old_logic2, new_logic2).replace(old_logic3, new_logic3)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code)
