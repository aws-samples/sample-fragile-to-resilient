"""Benchmark: prove summarize_batch overlaps its waiting.

We monkeypatch fde.batch.ask with a fake that just sleeps 1s (standing in for
a ~1s Bedrock network wait), then time three runs over 10 documents:

  1. serial      — plain for-loop calling ask() one at a time  (expect ~10s)
  2. async x10   — summarize_batch, max_concurrency=10          (expect ~1s)
  3. async x3    — summarize_batch, max_concurrency=3           (expect ~4s:
                   10 docs / 3 permits = 4 waves of ~1s)

Run:  python scripts/batch_benchmark.py
"""

import asyncio
import time

import fde.batch
from fde.batch import summarize_batch


def fake_ask(document: str) -> str:
    """Stand-in for the real ask(): blocks 1s like a network call, no AWS."""
    time.sleep(1)
    return f"summary of: {document}"


# Same trick as the tests: swap the real ask for the fake where it's looked up.
fde.batch.ask = fake_ask

DOCS = [f"insurance document #{i}" for i in range(10)]


def run_serial() -> float:
    start = time.perf_counter()
    results = [fake_ask(doc) for doc in DOCS]
    elapsed = time.perf_counter() - start
    assert len(results) == 10
    return elapsed


def run_async(max_concurrency: int) -> float:
    start = time.perf_counter()
    results = asyncio.run(summarize_batch(DOCS, max_concurrency=max_concurrency))
    elapsed = time.perf_counter() - start
    assert len(results) == 10
    assert results[0].endswith("#0")  # gather preserves input order
    return elapsed


if __name__ == "__main__":
    serial = run_serial()
    wide = run_async(max_concurrency=10)
    narrow = run_async(max_concurrency=3)

    print(f"serial (1 at a time):     {serial:5.2f}s")
    print(f"async (concurrency=10):   {wide:5.2f}s  ~{serial / wide:.1f}x faster")
    print(f"async (concurrency=3):    {narrow:5.2f}s  ~{serial / narrow:.1f}x faster")
