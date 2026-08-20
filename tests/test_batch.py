import asyncio
import threading

import pytest

import fde.batch
from fde.batch import summarize_batch


def test_batch_returns_summaries_in_input_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fde.batch, "ask", lambda doc: f"summary of: {doc}")

    docs = [f"doc {i}" for i in range(10)]
    results = asyncio.run(summarize_batch(docs))

    assert results == [f"summary of: doc {i}" for i in range(10)]


def test_batch_never_exceeds_max_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    in_flight = 0
    peak = 0
    lock = threading.Lock()

    def tracking_ask(doc: str) -> str:
        nonlocal in_flight, peak
        with lock:
            in_flight += 1
            peak = max(peak, in_flight)
        try:
            # Yield the thread so other workers get a chance to overlap.
            threading.Event().wait(0.01)
            return f"summary of: {doc}"
        finally:
            with lock:
                in_flight -= 1

    monkeypatch.setattr(fde.batch, "ask", tracking_ask)

    docs = [f"doc {i}" for i in range(10)]
    asyncio.run(summarize_batch(docs, max_concurrency=3))

    assert peak <= 3


def test_batch_propagates_a_failing_document(monkeypatch: pytest.MonkeyPatch) -> None:
    def flaky_ask(doc: str) -> str:
        if doc == "doc 3":
            raise RuntimeError("retries exhausted")
        return f"summary of: {doc}"

    monkeypatch.setattr(fde.batch, "ask", flaky_ask)

    docs = [f"doc {i}" for i in range(5)]
    with pytest.raises(RuntimeError, match="retries exhausted"):
        asyncio.run(summarize_batch(docs))
