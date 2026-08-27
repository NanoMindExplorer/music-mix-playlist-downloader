"""
Concurrent downloads via ThreadPoolExecutor.

Sebelumnya, download playlist Spotify dilakukan sequential:
    for track in spotify_targets:
        ydl.download([f"ytsearch1:{track}"])

Untuk playlist 50 lagu dengan avg 5 detik per search+download = 250 detik
total. Dengan concurrent 3 worker = ~85 detik (3x speedup).

ThreadPool dipilih (bukan ProcessPool) karena:
    - yt-dlp sudah handle GIL via internal C extensions untuk network I/O
    - Lower memory footprint (share process state)
    - Setup overhead minimal

Trade-off:
    - YouTube rate limit: jangan terlalu agresif (>5 concurrent → 429 risk)
    - Disk I/O bottleneck: kalau storage lambat, parallel tidak membantu
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

from mmpd.logger import get_logger

_log = get_logger()


@dataclass
class ConcurrentResult:
    """Hasil satu task concurrent."""

    success: bool
    item: str                       # Item yang diproses (untuk identifikasi)
    error: Optional[str] = None
    extra: dict = field(default_factory=dict)  # Untuk metadata tambahan


def run_concurrent(
    items: List[str],
    worker_fn: Callable[[str], Tuple[bool, Optional[str], dict]],
    max_workers: int = 3,
    description: str = "downloading",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> List[ConcurrentResult]:
    """
    Jalankan worker_fn untuk setiap item secara parallel.

    Args:
        items:             List item untuk diproses
        worker_fn:         Function signature: (item) -> (success, error, extra_dict)
        max_workers:       Jumlah thread paralel (default 3)
        description:       Label untuk logging ("downloading", "matching", etc.)
        progress_callback: Optional callback (completed, total, current_item)

    Returns:
        List ConcurrentResult, urut sama dengan input items.

    Example:
        def worker(url):
            try:
                ydl.download([url])
                return True, None, {}
            except Exception as e:
                return False, str(e), {}

        results = run_concurrent(
            items=["url1", "url2", "url3"],
            worker_fn=worker,
            max_workers=3,
        )
        for r in results:
            print(f"{r.item}: {'OK' if r.success else 'FAIL: ' + (r.error or '')}")
    """
    if not items:
        return []

    if len(items) == 1:
        # Single item, skip thread pool overhead
        _log.debug("Concurrent: single item, skip thread pool")
        success, error, extra = worker_fn(items[0])
        return [ConcurrentResult(success=success, item=items[0], error=error, extra=extra)]

    # Batasi max_workers agar tidak exceed items count
    actual_workers = min(max_workers, len(items))
    _log.info(
        "Concurrent %s: %d items with %d workers",
        description,
        len(items),
        actual_workers,
    )

    results: List[ConcurrentResult] = [None] * len(items)  # type: ignore[list-item]
    completed_count = 0
    total_count = len(items)

    # Map future → index agar bisa urut balik
    future_to_index: dict = {}

    with ThreadPoolExecutor(max_workers=actual_workers, thread_name_prefix="mmpd") as executor:
        for idx, item in enumerate(items):
            future = executor.submit(worker_fn, item)
            future_to_index[future] = idx

        for future in as_completed(future_to_index):
            idx = future_to_index[future]
            item = items[idx]
            completed_count += 1

            try:
                success, error, extra = future.result()
                results[idx] = ConcurrentResult(
                    success=success,
                    item=item,
                    error=error,
                    extra=extra,
                )
                if success:
                    _log.debug(
                        "Concurrent [%d/%d] OK: %s",
                        completed_count,
                        total_count,
                        item[:60],
                    )
                else:
                    _log.warning(
                        "Concurrent [%d/%d] FAIL: %s — %s",
                        completed_count,
                        total_count,
                        item[:60],
                        error,
                    )
            except Exception as e:
                # Exception dari worker_fn itu sendiri
                results[idx] = ConcurrentResult(
                    success=False,
                    item=item,
                    error=f"{type(e).__name__}: {e}",
                )
                _log.error(
                    "Concurrent [%d/%d] EXCEPTION: %s — %s",
                    completed_count,
                    total_count,
                    item[:60],
                    e,
                )

            if progress_callback:
                progress_callback(completed_count, total_count, item)

    # Stats
    success_count = sum(1 for r in results if r and r.success)
    fail_count = total_count - success_count
    _log.info(
        "Concurrent %s complete: %d success, %d fail (of %d total, %d workers)",
        description,
        success_count,
        fail_count,
        total_count,
        actual_workers,
    )

    return results
