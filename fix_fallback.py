with open("mmpd/utils/matching.py", "r") as f:
    code = f.read()

code = code.replace("norm_source = normalize_title(source)", "norm_source = normalize_title(source_comp)")
code = code.replace("for c in candidates:", "for idx, c in enumerate(candidates_comp):")
code = code.replace("return c", "return candidates[idx]")
with open("mmpd/utils/matching.py", "w") as f:
    f.write(code)
