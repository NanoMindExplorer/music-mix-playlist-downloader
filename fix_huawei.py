import os
with open("mmpd/modes/retrofit.py", "r") as f:
    code = f.read()

old_logic = """    # Hapus lirik lama jika diminta
    if force_overwrite_lrc and os.path.exists(lrc_path):
        os.remove(lrc_path)"""

new_logic = """    # Hapus lirik lama jika diminta
    if force_overwrite_lrc:
        if os.path.exists(lrc_path):
            os.remove(lrc_path)
        huawei_lrc_path = os.path.join(
            str(Path.home()), "storage", "shared", "Music", "Musiclrc", f"{title}.lrc"
        )
        if os.path.exists(huawei_lrc_path):
            os.remove(huawei_lrc_path)"""

code = code.replace(old_logic, new_logic)
with open("mmpd/modes/retrofit.py", "w") as f:
    f.write(code)
