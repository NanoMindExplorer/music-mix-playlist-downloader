from deep_translator import GoogleTranslator
import re

lrc = """[00:01.00] 窓を開けて
[00:03.00] 空を見上げて"""

lines = lrc.splitlines()
translator = GoogleTranslator(source='auto', target='id')

# Extract text to translate
texts_to_translate = []
for line in lines:
    text = re.sub(r'\[.*?\]', '', line).strip()
    texts_to_translate.append(text if text else " ") # append space if empty to keep index

# Translate batch
translated_texts = translator.translate_batch(texts_to_translate)

# Reconstruct
output = []
for i, line in enumerate(lines):
    output.append(line)
    if translated_texts[i].strip():
        # append translation without timestamp
        output.append(f"({translated_texts[i].strip()})")

print("\n".join(output))
