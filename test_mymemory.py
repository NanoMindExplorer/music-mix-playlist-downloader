from deep_translator import MyMemoryTranslator

texts = ["窓を開けて", "空を見上げて"]
try:
    print(MyMemoryTranslator(source='ja-JP', target='id-ID').translate_batch(texts))
except Exception as e:
    print(f"MyMemory failed: {e}")
