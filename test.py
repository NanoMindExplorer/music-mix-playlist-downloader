import re

lines = [
    "[00:01.00]Hello world\n",
    "[00:05.00]This is a test\n"
]
texts_to_translate = ["Hello world", "This is a test"]
translated_texts = ["Halo dunia", "Ini adalah tes"]

output = []
for i, line in enumerate(lines):
    t_text = translated_texts[i].strip() if translated_texts[i] else ""
    if t_text and t_text.lower() != texts_to_translate[i].strip().lower():
        match = re.match(r"(\[.*?\])", line)
        if match:
            timestamp = match.group(1)
            original_text = line[len(timestamp):].rstrip("\n")
            combined_line = (
                f'{timestamp}'
                f'<font color="#FFFFFF">{original_text}</font>'
                f'<br>'
                f'<font color="#00FFFF"><small>{t_text}</small></font>'
            )
            output.append(combined_line)
        else:
            output.append(line.rstrip("\n"))
    else:
        output.append(line.rstrip("\n"))

for x in output: print(x)
