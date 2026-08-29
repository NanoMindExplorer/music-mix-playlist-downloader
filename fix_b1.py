import re
with open("mmpd/lyrics.py", "r") as f:
    code = f.read()
code = code.replace("time_tag = re.match(r\"\\[.*?\\]\", line)", "time_tags = \"\".join(re.findall(r\"\\[.*?\\]\", line))")
code = code.replace("time_tag.group(0) if time_tag else ''", "time_tags")
with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
