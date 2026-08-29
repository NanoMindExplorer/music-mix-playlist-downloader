"""
Huawei Musiclrc sync — copy .lrc ke folder khusus Huawei/HarmonyOS.

Dipisah dari pipeline utama (Fase A) karena ini murni operasi filesystem
yang bergantung environment (hanya aktif di Termux/Android).
"""

from __future__ import annotations

import os
import shutil

from mmpd.config import get_musiclrc_dir
from mmpd.logger import get_logger

_log = get_logger()


def sync_huawei_lrc(lrc_path: str) -> None:
    """
    Salin file .lrc ke folder khusus Musiclrc bawaan Huawei/Android.

    Kebutuhan: Huawei Music Player mensyaratkan lirik (.lrc) berada di
    folder `Internal/Music/Musiclrc`. Tanpa sync ini, lirik tidak muncul
    di karaoke mode Huawei.

    Args:
        lrc_path: Path file .lrc yang akan di-sync.

    Behavior:
        - Hanya jalan di Termux (skip di Linux/macOS/Windows)
        - Best-effort: kegagalan copy tidak pernah raise (cuma warning log)
    """
    huawei_dir = get_musiclrc_dir()
    try:
        os.makedirs(huawei_dir, exist_ok=True)
        filename = os.path.basename(lrc_path)
        target = os.path.join(huawei_dir, filename)
        shutil.copy2(lrc_path, target)
        _log.debug("LRC synced to Huawei Musiclrc: %s", filename)
    except Exception as e:
        _log.warning("sync_huawei_lrc failed for %s: %s", os.path.basename(lrc_path), e)
