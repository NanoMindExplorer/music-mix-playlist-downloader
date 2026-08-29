with open("mmpd/utils/matching.py", "r") as f:
    code = f.read()

old_block = """def fuzzy_match(
    source: str,
    candidates: list[str],
    threshold: int = 50,
) -> Optional[str]:
    \"\"\"
    Cari best match dari candidates berdasarkan fuzzy string matching.

    Args:
        source:     String source (mis. nama file .lrc tanpa extension)
        candidates: List candidate strings (mis. semua nama file .mp3)
        threshold:  Score minimum 0-100 untuk dianggap match (default 50)

    Returns:
        Best matching candidate, atau None jika tidak ada yang >= threshold.

    Examples:
        >>> fuzzy_match("Adele - Hello", ["Adele Hello.mp3", "Random.mp3"])
        'Adele Hello'
    \"\"\"
    try:
        from rapidfuzz import fuzz
    except ImportError:"""

new_block = """def fuzzy_match(
    source: str,
    candidates: list[str],
    threshold: int = 50,
) -> Optional[str]:
    \"\"\"
    Cari best match dari candidates berdasarkan fuzzy string matching.
    \"\"\"
    try:
        import opencc
        converter = opencc.OpenCC('t2s')
        source_comp = converter.convert(source)
        candidates_comp = [converter.convert(c) for c in candidates]
    except ImportError:
        source_comp = source
        candidates_comp = candidates

    try:
        from rapidfuzz import fuzz
    except ImportError:"""

code = code.replace(old_block, new_block)

old_logic = """    norm_source = normalize_title(source)
    best_match: Optional[str] = None
    best_score = 0

    for candidate in candidates:
        norm_candidate = normalize_title(candidate)
        score = fuzz.ratio(norm_source, norm_candidate)"""

new_logic = """    norm_source = normalize_title(source_comp)
    best_match: Optional[str] = None
    best_score = 0

    for idx, candidate in enumerate(candidates_comp):
        norm_candidate = normalize_title(candidate)
        score = fuzz.ratio(norm_source, norm_candidate)"""

code = code.replace(old_logic, new_logic)

code = code.replace("""if score > best_score:
            best_score = score
            best_match = candidate""", """if score > best_score:
            best_score = score
            best_match = candidates[idx]""")

with open("mmpd/utils/matching.py", "w") as f:
    f.write(code)
