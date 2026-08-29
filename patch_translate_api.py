import re

with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

new_logic = """def _worker_translate(text: str, source_lang: str) -> tuple[bool, str | None, dict]:
    try:
        res = _translate_one_with_fallback(text, source_lang)
        return True, None, {"text": res}
    except Exception as e:
        return False, str(e), {}

def _translate_via_api(texts_to_translate, source_lang: str = "auto"):
    \"\"\"
    Translate list of texts ke Indonesia.
    Strategi:
        1. Batch bernomor lewat Google (konteks antar-baris → lebih akurat)
        2. Baris yang gagal di-batch di-retry paralel dengan run_concurrent
        3. Satu baris gagal TIDAK menggagalkan seluruh lagu
    \"\"\"
    n = len(texts_to_translate)
    translated_texts = [" "] * n
    
    pending = []
    for i, text in enumerate(texts_to_translate):
        if text and text.strip():
            pending.append(i)
        else:
            translated_texts[i] = " "
            
    BATCH = 10
    i = 0
    from mmpd.concurrent import run_concurrent
    
    while i < len(pending):
        chunk_idx = pending[i:i + BATCH]
        chunk_txt = [texts_to_translate[j] for j in chunk_idx]
        used_batch = False
        if len(chunk_txt) >= 3:
            import time
            for attempt in range(3):
                try:
                    parsed = _translate_batch_google(chunk_txt, source_lang)
                    ok = 0
                    for local, global_i in enumerate(chunk_idx):
                        val = parsed[local] if parsed and local < len(parsed) and parsed[local] else None
                        if val and not _looks_like_failed_translation(chunk_txt[local], val):
                            translated_texts[global_i] = val
                            ok += 1
                    if ok >= max(1, len(chunk_txt) // 2):
                        used_batch = True
                        # Sisa yang kosong dikumpulkan
                        missing_idx = []
                        missing_txt = []
                        for local, global_i in enumerate(chunk_idx):
                            if translated_texts[global_i].strip() in ("",):
                                missing_idx.append(global_i)
                                missing_txt.append(chunk_txt[local])
                        if missing_txt:
                            res = run_concurrent(
                                missing_txt,
                                lambda t: _worker_translate(t, source_lang),
                                max_workers=5,
                                description="Retry translate"
                            )
                            for local_m, global_i in enumerate(missing_idx):
                                if res[local_m] and "text" in res[local_m]:
                                    translated_texts[global_i] = res[local_m]["text"]
                    break  # Success, exit retry loop
                except Exception as e:
                    _log.debug("Google batch attempt %d gagal (%s)", attempt + 1, e)
                    time.sleep(2)  # D3: backoff
            
        if not used_batch:
            res = run_concurrent(
                chunk_txt,
                lambda t: _worker_translate(t, source_lang),
                max_workers=5,
                description="Fallback translate"
            )
            for local, global_i in enumerate(chunk_idx):
                if res[local] and "text" in res[local]:
                    translated_texts[global_i] = res[local]["text"]
                    
        i += BATCH
        if i < len(pending):
            import time
            time.sleep(0.5)  # D3: jeda 0.5 detik antar batch
            
    filled = sum(1 for t in translated_texts if t and t.strip())
    _log.info("Translation API: %d/%d baris berhasil (src=%s)", filled, len(pending), source_lang)
    return translated_texts"""

# Match everything from "def _translate_via_api(" until "def _write_bilingual_lrc("
pattern = r"def _translate_via_api\(texts_to_translate, source_lang: str = \"auto\"\):.*?def _write_bilingual_lrc\("
code = re.sub(pattern, new_logic + "\n\n\ndef _write_bilingual_lrc(", code, flags=re.DOTALL)

with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
