import re, os
from deep_translator import GoogleTranslator, MyMemoryTranslator
import langdetect

def process_translation(lrc_path):
    try:
        with open(lrc_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        texts_to_translate = []
        for line in lines:
            text = re.sub(r'\[.*?\]', '', line).strip()
            texts_to_translate.append(text if text else " ")

        translated_texts = []
        try:
            translator = GoogleTranslator(source='auto', target='id')
            translated_texts = translator.translate_batch(texts_to_translate)
            if any(t and "Error 500" in t for t in translated_texts):
                raise Exception("Google Translate Web API Error 500")
        except Exception as e:
            print(f"Google Translate gagal: {e}. Mencoba MyMemory fallback...")
            pure_text = " ".join([t for t in texts_to_translate if t.strip()])
            if not pure_text: return
            lang = langdetect.detect(pure_text)
            
            lang_map = {'ja': 'ja-JP', 'zh-cn': 'zh-CN', 'zh-tw': 'zh-TW', 'ko': 'ko-KR', 'th': 'th-TH', 'en': 'en-US'}
            source_lang = lang_map.get(lang, f"{lang}-{lang.upper()}")
            
            try:
                mm = MyMemoryTranslator(source=source_lang, target='id-ID')
                translated_texts = mm.translate_batch(texts_to_translate)
            except Exception as e2:
                print(f"MyMemory juga gagal: {e2}")
                return

        if not translated_texts or len(translated_texts) != len(lines):
            return

        output = []
        for i, line in enumerate(lines):
            output.append(line.rstrip('\n'))
            t_text = translated_texts[i].strip() if translated_texts[i] else ""
            if t_text and t_text.lower() != texts_to_translate[i].strip().lower():
                match = re.match(r'(\[.*?\])', line)
                if match:
                    timestamp = match.group(1)
                    output.append(f"{timestamp} ({t_text})")
                    
        with open(lrc_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(output))
            
    except Exception as e:
        print(f"Gagal translate: {e}")

with open('test.lrc', 'w') as f:
    f.write("[00:01.00] 窓を開けて\n[00:03.00] 空を見上げて\n[00:05.00] Music")
process_translation('test.lrc')
print(open('test.lrc').read())
