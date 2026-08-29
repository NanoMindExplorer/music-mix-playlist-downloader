import re

with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

old_func = """def _translate_via_api(texts_to_translate):
    \"\"\"
    Translate list of texts via Google Translate (fallback MyMemory).
    Dipisah ke function terpisah untuk readability + testability (Fase 4).
    \"\"\"
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    import langdetect

    translated_texts = []

    # === Strategi 1: Google Translate (batch, cepat) ===
    try:
        translator = GoogleTranslator(source="auto", target="id")
        combined_text = "\\n".join(texts_to_translate)
        res = translator.translate(combined_text)
        if not res or "Error 500" in res:
            raise Exception("Google Translate Web API Error 500")
        translated_texts = res.split("\\n")
        return translated_texts
    except Exception as e:
        _log.warning("Google Translate gagal (%s). Beralih ke MyMemory...", e)

        # === Strategi 2: MyMemory (chunked, lebih lambat tapi reliable) ===
        pure_text = " ".join([t for t in texts_to_translate if t.strip()])
        if not pure_text:
            return [" "] * len(texts_to_translate)
        try:
            source_lang = langdetect.detect(pure_text)
        except Exception:
            source_lang = "en"

        try:
            translator_mm = MyMemoryTranslator(source=source_lang, target="id")
            for line in texts_to_translate:
                if not line.strip():
                    translated_texts.append(" ")
                    continue
                mm_res = translator_mm.translate(line)
                if not mm_res:
                    translated_texts.append(" ")
                elif "MYMEMORY WARNING" in mm_res:
                    _log.error("MyMemory Rate Limit Tercapai. Lirik tersisa akan dilewati.")
                    raise Exception("MyMemory Rate Limit")
                else:
                    translated_texts.append(mm_res)
            return translated_texts
        except Exception as e:
            _log.error("MyMemory gagal: %s. Proses terjemahan dihentikan.", e)
            return [""] * len(texts_to_translate)"""

new_func = """def _translate_via_api(texts_to_translate):
    \"\"\"
    Translate list of texts via Google Translate (fallback MyMemory).
    Dipisah ke function terpisah untuk readability + testability (Fase 4).
    \"\"\"
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    import concurrent.futures
    import langdetect

    translated_texts = [""] * len(texts_to_translate)
    
    # === Strategi 1: Google Translate (concurrency per baris) ===
    try:
        translator = GoogleTranslator(source="auto", target="id")
        
        def _trans_google(idx, text):
            if not text.strip(): return idx, " "
            try:
                res = translator.translate(text)
                if not res or "Error 500" in res:
                    raise Exception("API Error")
                return idx, res
            except Exception:
                raise

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(_trans_google, i, t) for i, t in enumerate(texts_to_translate)]
            for f in concurrent.futures.as_completed(futures):
                idx, res = f.result()
                translated_texts[idx] = res
        return translated_texts
    except Exception as e:
        _log.warning("Google Translate gagal (%s). Beralih ke MyMemory...", e)

        # === Strategi 2: MyMemory (chunked, lebih lambat tapi reliable) ===
        pure_text = " ".join([t for t in texts_to_translate if t.strip()])
        if not pure_text:
            return [" "] * len(texts_to_translate)
        try:
            source_lang = langdetect.detect(pure_text)
        except Exception:
            source_lang = "en"

        try:
            translator_mm = MyMemoryTranslator(source=source_lang, target="id")
            def _trans_mm(idx, text):
                if not text.strip(): return idx, " "
                res = translator_mm.translate(text)
                if not res: return idx, " "
                if "MYMEMORY WARNING" in res:
                    raise Exception("MyMemory Rate Limit")
                return idx, res

            translated_texts_mm = [""] * len(texts_to_translate)
            # Use max_workers=2 for MyMemory to avoid rate limits
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(_trans_mm, i, t) for i, t in enumerate(texts_to_translate)]
                for f in concurrent.futures.as_completed(futures):
                    idx, res = f.result()
                    translated_texts_mm[idx] = res
            return translated_texts_mm
        except Exception as e:
            _log.error("MyMemory gagal: %s. Proses terjemahan dihentikan.", e)
            return [""] * len(texts_to_translate)"""

if old_func in code:
    code = code.replace(old_func, new_func)
    with open("mmpd/lyrics.py", "w") as f:
        f.write(code)
    print("Replaced!")
else:
    print("Old func not found!")
