"""
Unit tests untuk mmpd.concurrent — ThreadPoolExecutor wrapper.

Coverage:
    - run_concurrent basic execution
    - Single item skips thread pool
    - Multiple items parallel execution
    - Exception isolation (one worker crash doesn't fail others)
    - Progress callback invocation
    - ConcurrentResult dataclass
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from mmpd.concurrent import ConcurrentResult, run_concurrent


# ============================================================================
# ConcurrentResult dataclass
# ============================================================================

class TestConcurrentResult:
    def test_basic_creation(self):
        """Test buat ConcurrentResult."""
        result = ConcurrentResult(success=True, item="test_item")
        assert result.success is True
        assert result.item == "test_item"
        assert result.error is None
        assert result.extra == {}

    def test_with_error(self):
        """Test ConcurrentResult dengan error."""
        result = ConcurrentResult(
            success=False,
            item="failed_item",
            error="ConnectionError",
        )
        assert result.success is False
        assert result.error == "ConnectionError"

    def test_with_extra(self):
        """Test ConcurrentResult dengan extra metadata."""
        result = ConcurrentResult(
            success=True,
            item="item1",
            extra={"video_url": "https://youtube.com/watch?v=abc"},
        )
        assert result.extra["video_url"] == "https://youtube.com/watch?v=abc"

    def test_extra_default_empty_dict(self):
        """Test extra default empty dict."""
        result = ConcurrentResult(success=True, item="test")
        assert result.extra == {}
        # Modify extra — should not affect other instances
        result.extra["key"] = "value"
        result2 = ConcurrentResult(success=True, item="test2")
        assert result2.extra == {}


# ============================================================================
# run_concurrent — basic execution
# ============================================================================

class TestRunConcurrent:
    def test_empty_items_returns_empty_list(self):
        """Test empty items list return empty list."""
        results = run_concurrent([], lambda x: (True, None, {}))
        assert results == []

    def test_single_item_skips_thread_pool(self):
        """Test single item skip thread pool overhead."""
        called = []

        def worker(item):
            called.append(item)
            return (True, None, {"processed": True})

        results = run_concurrent(["single"], worker, max_workers=3)
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].item == "single"
        assert results[0].extra["processed"] is True
        assert called == ["single"]

    def test_multiple_items_all_succeed(self):
        """Test multiple items semua sukses."""
        items = ["item1", "item2", "item3", "item4"]

        def worker(item):
            return (True, None, {"length": len(item)})

        results = run_concurrent(items, worker, max_workers=2)
        assert len(results) == 4
        assert all(r.success for r in results)
        # Verify order preserved
        assert results[0].item == "item1"
        assert results[1].item == "item2"
        assert results[2].item == "item3"
        assert results[3].item == "item4"

    def test_results_preserve_order(self):
        """Test results list urut sama dengan input items."""
        items = ["c", "a", "b", "d", "e"]

        def worker(item):
            # Simulate variable processing time
            time.sleep(0.01 * (ord(item) % 5))
            return (True, None, {})

        results = run_concurrent(items, worker, max_workers=3)
        # Order should match input
        for i, expected in enumerate(items):
            assert results[i].item == expected

    def test_max_workers_capped_at_items_length(self):
        """Test max_workers tidak exceed items count."""
        items = ["a", "b"]  # Only 2 items

        def worker(item):
            return (True, None, {})

        # max_workers=10 but only 2 items → actual workers = 2
        results = run_concurrent(items, worker, max_workers=10)
        assert len(results) == 2
        # All should succeed (test doesn't crash)


# ============================================================================
# run_concurrent — exception handling
# ============================================================================

class TestRunConcurrentExceptionHandling:
    def test_worker_exception_returns_failure_result(self):
        """Test worker yang raise exception tetap return ConcurrentResult (not crash)."""
        items = ["good", "bad", "good2"]

        def worker(item):
            if item == "bad":
                raise RuntimeError("Worker crashed")
            return (True, None, {})

        results = run_concurrent(items, worker, max_workers=2)
        assert len(results) == 3
        # "good" and "good2" should succeed
        success_items = [r for r in results if r.success]
        assert len(success_items) >= 2
        # "bad" should be in failure results
        failure_items = [r for r in results if not r.success]
        assert len(failure_items) == 1
        assert failure_items[0].item == "bad"
        assert "RuntimeError" in failure_items[0].error

    def test_worker_returning_failure_tuple(self):
        """Test worker return (False, error_msg, {}) → ConcurrentResult dengan error."""
        items = ["good", "bad"]

        def worker(item):
            if item == "bad":
                return (False, "Download failed", {})
            return (True, None, {})

        results = run_concurrent(items, worker, max_workers=2)
        assert results[0].success is True  # "good"
        assert results[1].success is False  # "bad"
        assert results[1].error == "Download failed"

    def test_one_failure_does_not_affect_others(self):
        """Test satu worker gagal tidak menghentikan worker lain."""
        items = ["a", "fail", "b", "c", "d"]

        def worker(item):
            if item == "fail":
                raise Exception("Crash")
            return (True, None, {"item": item})

        results = run_concurrent(items, worker, max_workers=2)
        # All 5 items should have results
        assert len(results) == 5
        # 4 should succeed
        success = [r for r in results if r.success]
        assert len(success) == 4
        # 1 should fail
        failures = [r for r in results if not r.success]
        assert len(failures) == 1
        assert failures[0].item == "fail"


# ============================================================================
# run_concurrent — progress callback
# ============================================================================

class TestRunConcurrentProgressCallback:
    def test_progress_callback_invoked(self):
        """Test progress_callback dipanggil setelah setiap item selesai."""
        items = ["a", "b", "c"]
        progress_calls = []

        def worker(item):
            return (True, None, {})

        def progress(completed, total, current):
            progress_calls.append((completed, total, current))

        run_concurrent(items, worker, max_workers=2, progress_callback=progress)
        assert len(progress_calls) == 3
        # First call: completed=1, total=3
        assert progress_calls[0][0] == 1
        assert progress_calls[0][1] == 3
        # Last call: completed=3, total=3
        assert progress_calls[-1][0] == 3
        assert progress_calls[-1][1] == 3

    def test_progress_callback_not_required(self):
        """Test progress_callback optional (None default)."""
        items = ["a", "b"]

        def worker(item):
            return (True, None, {})

        # Should not raise with progress_callback=None
        results = run_concurrent(items, worker, max_workers=2, progress_callback=None)
        assert len(results) == 2

    def test_progress_callback_skipped_for_single_item(self):
        """Test progress_callback tidak dipanggil untuk single item (skip thread pool)."""
        items = ["single"]
        progress_calls = []

        def worker(item):
            return (True, None, {})

        def progress(completed, total, current):
            progress_calls.append((completed, total, current))

        run_concurrent(items, worker, max_workers=3, progress_callback=progress)
        # Single item skips thread pool, no callback
        assert len(progress_calls) == 0


# ============================================================================
# run_concurrent — concurrency verification
# ============================================================================

class TestRunConcurrentActuallyParallel:
    def test_parallel_faster_than_sequential(self):
        """Test bahwa concurrent lebih cepat dari sequential untuk I/O-bound work."""
        items = ["a", "b", "c", "d"]
        sleep_time = 0.2  # 200ms per item

        def worker(item):
            time.sleep(sleep_time)
            return (True, None, {})

        # Sequential time = 4 * 0.2 = 0.8s
        # Parallel time (3 workers) = max(0.2, 0.2, 0.2, 0.2) ≈ 0.4s
        start = time.monotonic()
        results = run_concurrent(items, worker, max_workers=3)
        elapsed = time.monotonic() - start

        assert len(results) == 4
        # Should be faster than sequential (allow some margin)
        # 4 items, 3 workers → 2 batches × 0.2s = 0.4s minimum
        # Allow up to 0.6s for thread overhead
        assert elapsed < 0.6, f"Concurrent took {elapsed:.2f}s, expected < 0.6s"
