import re
import os

with open("mmpd/lyrics.py", "r") as f:
    code = f.read()

# Find the start and end of _write_bilingual_lrc
import ast

def get_function_bounds(source, func_name):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return node.lineno, node.end_lineno
    return None, None

start, end = get_function_bounds(code, "_write_bilingual_lrc")
lines = code.split("\n")
old_func = "\n".join(lines[start-1:end])

new_func = """def _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts):
    \"\"\"
    Tulis file LRC bilingual dengan format standar industri atau gabungan.
    Konfigurasi format via ENV `MMPD_BILINGUAL_FORMAT` (gabung, pisah, id_only).
    \"\"\"
    import os
    format_mode = os.environ.get("MMPD_BILINGUAL_FORMAT", "gabung")

    if len(translated_texts) < len(lines):
        translated_texts.extend([""] * (len(lines) - len(translated_texts)))

    def _parse_ts(ts_str):
        # ts_str is like "[00:01.23]"
        m = re.match(r"\\[(\\d+):(\\d+\\.\\d+)\\]", ts_str)
        if not m: return None
        return int(m.group(1)) * 60 + float(m.group(2))

    def _format_ts(seconds):
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"[{mins:02d}:{secs:05.2f}]"

    # Pre-parse timestamps untuk micro-offset
    parsed_lines = []
    for line in lines:
        match = re.match(r"(\\[\\d+:\\d+\\.\\d+\\])", line)
        ts_val = _parse_ts(match.group(1)) if match else None
        parsed_lines.append((line, match.group(1) if match else None, ts_val))

    output = []
    output_id = []
    
    for i, (line, ts_str, ts_val) in enumerate(parsed_lines):
        t_text = translated_texts[i].strip() if translated_texts[i] else ""
        
        if t_text and t_text.lower() != texts_to_translate[i].strip().lower() and ts_str and ts_val is not None:
            original_text = line[len(ts_str):].rstrip("\\n")
            
            if format_mode == "pisah":
                # Cari next_ts
                next_ts = None
                for j in range(i + 1, len(parsed_lines)):
                    if parsed_lines[j][2] is not None:
                        next_ts = parsed_lines[j][2]
                        break
                
                # Offset logic
                DEFAULT_OFFSET = 0.6
                if next_ts is None:
                    new_ts_val = ts_val + DEFAULT_OFFSET
                else:
                    gap = next_ts - ts_val
                    new_ts_val = ts_val + min(DEFAULT_OFFSET, gap * 0.4)
                
                new_ts_str = _format_ts(new_ts_val)
                
                output.append(line.rstrip("\\n"))
                output.append(f'{new_ts_str}{t_text}')
            elif format_mode == "id_only":
                output.append(line.rstrip("\\n"))
                output_id.append(f'{ts_str}{t_text}')
            else:
                # Default: gabung
                combined_line = f'{ts_str}{original_text}  /  {t_text}'
                output.append(combined_line)
        else:
            output.append(line.rstrip("\\n"))
            if format_mode == "id_only" and ts_str:
                output_id.append(line.rstrip("\\n"))

    if format_mode == "id_only":
        id_path = lrc_path.replace(".lrc", ".id.lrc")
        atomic_write_text(id_path, "\\n".join(output_id))
    
    atomic_write_text(lrc_path, "\\n".join(output))
    _log.info("Translation OK: %s (mode=%s)", os.path.basename(lrc_path), format_mode)"""

code = code.replace(old_func, new_func)

with open("mmpd/lyrics.py", "w") as f:
    f.write(code)
print("Updated successfully")
