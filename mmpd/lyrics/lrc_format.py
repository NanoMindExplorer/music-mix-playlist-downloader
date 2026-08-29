"""
LRC format helpers — parse, render, dan penulisan bilingual.

Dipisah dari translate.py (Fase A) supaya:
- Format LRC (gabung/pisah/id_only) bisa di-test terpisah
- Model LyricLine (types.py) punya home untuk parse/render
- _looks_like_failed_translation bisa dipakai translate.py tanpa circular import
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from mmpd.logger import get_logger
from mmpd.types import LyricLine
from mmpd.utils.fs import atomic_write_text

_log = get_logger()

_LRC_TS_RE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
_LRC_ANY_TAG_RE = re.compile(r"\[.*?\]")


# ============================================================================
# Strip / parse dasar
# ============================================================================

def _strip_lrc_text(line: str) -> str:
    """Ambil teks lirik tanpa tag waktu / meta."""
    return re.sub(r"\[.*?\]", "", line).strip()


def parse_ts(ts_str: str) -> Optional[float]:
    """Parse '[mm:ss.xx]' → detik (float). None kalau bukan timestamp numerik."""
    m = _LRC_TS_RE.match(ts_str.strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + float(m.group(2))


def format_ts(seconds: float) -> str:
    """Detik → '[mm:ss.xx]' (negatif di-clamp ke 0)."""
    if seconds < 0:
        seconds = 0.0
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"[{mins:02d}:{secs:05.2f}]"


def parse_lrc_lines(lrc_text: str) -> List[LyricLine]:
    """Parse teks LRC mentah → List[LyricLine] (Fase A — API berbasis model).

    Baris metadata ([ti:], [ar:], dst.) di-skip. Hasil terurut naik by ts.
    """
    result: List[LyricLine] = []
    for line in lrc_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        m = _LRC_TS_RE.match(stripped)
        if not m:
            continue  # metadata / baris non-timestamp
        ts = int(m.group(1)) * 60 + float(m.group(2))
        text = _LRC_ANY_TAG_RE.sub("", stripped).strip()
        result.append(LyricLine(ts=ts, original=text))
    return sorted(result, key=lambda x: (x.ts is None, x.ts or 0))


def render_lrc(lines: List[LyricLine]) -> str:
    """List[LyricLine] → teks LRC siap tulis ke file."""
    return "\n".join(ln.to_lrc_line() for ln in lines) + "\n"


# ============================================================================
# Deteksi kualitas hasil terjemahan
# ============================================================================

def _looks_like_failed_translation(src: str, dest: str) -> bool:
    """True jika hasil terjemahan kosong, identik, atau masih aksara sumber."""
    if not dest or not dest.strip():
        return True
    s = src.strip().lower()
    d = dest.strip().lower()
    if s == d:
        return True
    if "error 500" in d or "mymemory warning" in d:
        return True
    from mmpd.lyrics.transliterate import detect_script

    src_script = detect_script(src)
    dest_script = detect_script(dest)
    if src_script != "latin" and dest_script == src_script:
        return True
    return False


# ============================================================================
# Deteksi bilingual
# ============================================================================

def is_already_bilingual(lines) -> bool:
    """Deteksi LRC yang sudah bilingual (gabung ' / ' atau pasangan micro-offset)."""
    payload = 0
    slash_hits = 0
    parsed = []
    for line in lines:
        text = _strip_lrc_text(line)
        if not text:
            continue
        payload += 1
        if "  /  " in line or " / " in line:
            slash_hits += 1
        m = re.match(r"\[(\d+):(\d+(?:\.\d+)?)\]", line)
        if m:
            ts = int(m.group(1)) * 60 + float(m.group(2))
            parsed.append((ts, text.lower()))

    if payload and slash_hits / payload >= 0.35:
        return True

    close_pairs = 0
    for i in range(len(parsed) - 1):
        gap = parsed[i + 1][0] - parsed[i][0]
        if 0 < gap <= 0.85 and parsed[i][1] != parsed[i + 1][1]:
            close_pairs += 1
    return close_pairs >= max(3, len(parsed) // 5) if parsed else False


# ============================================================================
# Penulisan bilingual (gabung / pisah / id_only)
# ============================================================================

def write_bilingual_from_lines(
    lrc_path: str,
    lines: List[LyricLine],
    format_mode: Optional[str] = None,
) -> int:
    """
    Tulis LRC bilingual dari List[LyricLine] (Fase A — API model-based).

    Setiap LyricLine yang punya id_text akan dirender sesuai format_mode:
      - gabung: '[ts]original  /  terjemahan' satu baris
      - pisah:  dua baris dengan micro-offset (Poweramp)
      - id_only: file utama tetap, terjemahan ke .id.lrc terpisah

    Returns: jumlah baris terjemahan yang ditulis.
    """
    format_mode = format_mode or os.environ.get("MMPD_BILINGUAL_FORMAT", "gabung")
    written = 0
    output: List[str] = []
    output_id: List[str] = []

    for i, ln in enumerate(lines):
        if ln.has_translation and ln.ts is not None:
            written += 1
            ts_str = format_ts(ln.ts)
            if format_mode == "pisah":
                next_ts = None
                for j in range(i + 1, len(lines)):
                    if lines[j].ts is not None:
                        next_ts = lines[j].ts
                        break
                DEFAULT_OFFSET = 0.6
                if next_ts is None:
                    new_ts = ln.ts + DEFAULT_OFFSET
                else:
                    gap = next_ts - ln.ts
                    new_ts = ln.ts + min(DEFAULT_OFFSET, max(0.25, gap * 0.4))
                output.append(f"{ts_str}{ln.original}")
                output.append(f"{format_ts(new_ts)}{ln.id_text}")
            elif format_mode == "id_only":
                output.append(f"{ts_str}{ln.original}")
                output_id.append(f"{ts_str}{ln.id_text}")
            else:  # gabung
                output.append(f"{ts_str}{ln.original}  /  {ln.id_text}")
        else:
            if ln.ts is not None:
                ts_str = format_ts(ln.ts)
                output.append(f"{ts_str}{ln.original}")
                if format_mode == "id_only":
                    output_id.append(f"{ts_str}{ln.original}")
            else:
                output.append(ln.original)

    if format_mode == "id_only" and output_id:
        id_path = lrc_path.replace(".lrc", ".id.lrc")
        atomic_write_text(id_path, "\n".join(output_id) + "\n")

    atomic_write_text(lrc_path, "\n".join(output) + "\n")
    return written


def _write_bilingual_lrc(lrc_path, lines, texts_to_translate, translated_texts):
    """
    Tulis file LRC bilingual dengan format standar industri atau gabungan.
    Konfigurasi format via ENV `MMPD_BILINGUAL_FORMAT` (gabung, pisah, id_only).

    (Legacy API berbasis list-of-raw-lines — tetap dipertahankan untuk
    backward compat dengan process_translation dan test lama.)
    """
    format_mode = os.environ.get("MMPD_BILINGUAL_FORMAT", "gabung")

    if len(translated_texts) < len(lines):
        translated_texts.extend([""] * (len(lines) - len(translated_texts)))

    def _parse_ts(ts_str):
        m = re.match(r"\[(\d+):(\d+\.\d+)\]", ts_str)
        if not m:
            m = re.match(r"\[(\d+):(\d+)\]", ts_str)
            if not m:
                return None
            return int(m.group(1)) * 60 + float(m.group(2))
        return int(m.group(1)) * 60 + float(m.group(2))

    def _format_ts(seconds):
        if seconds < 0:
            seconds = 0.0
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"[{mins:02d}:{secs:05.2f}]"

    parsed_lines = []
    for line in lines:
        match = re.match(r"(\[\d+:\d+(?:\.\d+)?\])", line)
        ts_val = _parse_ts(match.group(1)) if match else None
        parsed_lines.append((line, match.group(1) if match else None, ts_val))

    output = []
    output_id = []
    written = 0

    for i, (line, ts_str, ts_val) in enumerate(parsed_lines):
        t_text = translated_texts[i].strip() if translated_texts[i] else ""
        original_payload = texts_to_translate[i].strip() if i < len(texts_to_translate) else _strip_lrc_text(line)

        useful = (
            bool(t_text)
            and t_text.lower() != original_payload.lower()
            and not _looks_like_failed_translation(original_payload, t_text)
        )

        if useful and ts_str and ts_val is not None:
            original_text = line[len(ts_str):].rstrip("\n")
            written += 1
            if format_mode == "pisah":
                next_ts = None
                for j in range(i + 1, len(parsed_lines)):
                    if parsed_lines[j][2] is not None:
                        next_ts = parsed_lines[j][2]
                        break
                DEFAULT_OFFSET = 0.6
                if next_ts is None:
                    new_ts_val = ts_val + DEFAULT_OFFSET
                else:
                    gap = next_ts - ts_val
                    new_ts_val = ts_val + min(DEFAULT_OFFSET, max(0.25, gap * 0.4))
                new_ts_str = _format_ts(new_ts_val)
                output.append(line.rstrip("\n"))
                output.append(f"{new_ts_str}{t_text}")
            elif format_mode == "id_only":
                output.append(line.rstrip("\n"))
                output_id.append(f"{ts_str}{t_text}")
            else:
                combined_line = f"{ts_str}{original_text}  /  {t_text}"
                output.append(combined_line)
        else:
            output.append(line.rstrip("\n"))
            if format_mode == "id_only" and ts_str:
                output_id.append(line.rstrip("\n"))

    if format_mode == "id_only":
        id_path = lrc_path.replace(".lrc", ".id.lrc")
        atomic_write_text(id_path, "\n".join(output_id) + "\n")

    atomic_write_text(lrc_path, "\n".join(output) + "\n")
    _log.info(
        "Translation OK: %s (mode=%s, lines=%d)",
        os.path.basename(lrc_path),
        format_mode,
        written,
    )
