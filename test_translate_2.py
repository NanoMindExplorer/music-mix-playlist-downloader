from deep_translator import GoogleTranslator
import re

lrc = """[00:01.20] 窓を開けて
[00:03.45] 空を見上げて"""

lines = lrc.splitlines()
translator = GoogleTranslator(source='auto', target='id')

texts_to_translate = []
for line in lines:
    text = re.sub(r'\[.*?\]', '', line).strip()
    texts_to_translate.append(text if text else " ")

translated_texts = translator.translate_batch(texts_to_translate)

output = []
for i, line in enumerate(lines):
    output.append(line)
    if translated_texts[i].strip():
        match = re.match(r'(\[.*?\])', line)
        if match:
            timestamp = match.group(1)
            output.append(f"{timestamp} {translated_texts[i].strip()}")

print("\n".join(output))
