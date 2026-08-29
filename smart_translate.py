import time
from deep_translator import GoogleTranslator, MyMemoryTranslator

def smart_translate(texts, target_lang='id', source_lang='auto', use_mymemory=False):
    """
    Menerjemahkan list of texts dengan cara cerdas (menggabungkan teks agar menghemat kuota request)
    """
    # Filter teks yang kosong agar tidak membingungkan mesin
    filtered_texts = []
    for t in texts:
        filtered_texts.append(t if t.strip() else " ")
        
    translated_texts = []
    
    if not use_mymemory:
        # GOOGLE TRANSLATOR: Limit 5000 chars per request.
        # Kita gabungkan semua baris menjadi satu string raksasa
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            combined_text = "\n".join(filtered_texts)
            
            # Jika lebih dari 4500 karakter, kita split (walau sangat jarang terjadi untuk lirik)
            if len(combined_text) > 4500:
                raise Exception("Teks terlalu panjang untuk satu request Google")
                
            res = translator.translate(combined_text)
            if not res or "Error 500" in res:
                raise Exception("Google mengembalikan Error 500")
                
            translated_texts = res.split('\n')
        except Exception as e:
            raise e
            
    else:
        # MYMEMORY TRANSLATOR: Limit 500 chars per request & Max 5 requests/sec
        try:
            translator = MyMemoryTranslator(source=source_lang, target=target_lang)
            current_chunk = []
            current_len = 0
            
            for text in filtered_texts:
                if current_len + len(text) + 1 > 450:
                    # Translate chunk
                    combined = "\n".join(current_chunk)
                    res = translator.translate(combined)
                    translated_texts.extend(res.split('\n'))
                    current_chunk = [text]
                    current_len = len(text)
                    time.sleep(1) # Hindari Rate Limit
                else:
                    current_chunk.append(text)
                    current_len += len(text) + 1
                    
            if current_chunk:
                combined = "\n".join(current_chunk)
                res = translator.translate(combined)
                translated_texts.extend(res.split('\n'))
                
        except Exception as e:
            raise e
            
    # Pastikan jumlah baris terjemahan sama dengan aslinya (pad dengan kosong jika kurang)
    if len(translated_texts) < len(texts):
        translated_texts.extend([""] * (len(texts) - len(translated_texts)))
        
    return translated_texts

# Test
res1 = smart_translate(["窓を開けて", "空を見上げて", "", "Music"])
print("Google:", res1)
res2 = smart_translate(["窓を開けて", "空を見上げて", "", "Music"], source_lang='ja-JP', target_lang='id-ID', use_mymemory=True)
print("MyMemory:", res2)
