with open("mmpd/utils/matching.py", "r") as f:
    code = f.read()

old_logic = """def clean_search_query(title: str) -> str:
    \"\"\"
    Bersihkan judul dari kata kunci yang mengganggu pencarian lirik.
    Cocok untuk fallback jika ISRC gagal/tidak ada.
    \"\"\"
    if not title:
        return ""

    # Hapus [bracket], (parenthetical), 【japanese bracket】"""

new_logic = """def clean_search_query(title: str) -> str:
    \"\"\"
    Bersihkan judul dari kata kunci yang mengganggu pencarian lirik.
    Cocok untuk fallback jika ISRC gagal/tidak ada.
    \"\"\"
    if not title:
        return ""

    # Ekstrak core title sebelum kurung lirik (K)
    import re
    m = re.search(r'[『「【《]', title)
    if m and m.start() > 5:
        candidate = title[:m.start()].strip(" -–—")
        if len(candidate) >= 3:
            title = candidate

    # Hapus [bracket], (parenthetical), 【japanese bracket】"""

code = code.replace(old_logic, new_logic)
with open("mmpd/utils/matching.py", "w") as f:
    f.write(code)
