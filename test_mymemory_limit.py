from deep_translator import MyMemoryTranslator
text = "hello\n" * 100 # 600 characters
try:
    print("Translating 600 chars...")
    res = MyMemoryTranslator(source='en-US', target='id-ID').translate(text)
    print("Success. Length:", len(res))
except Exception as e:
    print(f"Failed: {e}")
