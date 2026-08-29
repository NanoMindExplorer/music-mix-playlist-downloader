from deep_translator import GoogleTranslator

lrc = [
    "窓を開けて",
    "空を見上げて",
    "Music",
    "This is a test of a long text"
]
combined = "\n".join(lrc)
try:
    translated_combined = GoogleTranslator(source='auto', target='id').translate(combined)
    translated_lines = translated_combined.split('\n')
    print("SUCCESS!")
    for t in translated_lines:
        print(t)
except Exception as e:
    print(f"FAILED: {e}")
