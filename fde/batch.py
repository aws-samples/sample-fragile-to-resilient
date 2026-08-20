"""Summarize a batch of documents concurrently, reusing the sync ask()"""

import asyncio

from .bedrock_client import ask


async def summarize_one(document: str, semaphore: asyncio.Semaphore) -> str:
    """Summarize a single document, holding a semaphore permit while it runs."""
    async with semaphore:
        return await asyncio.to_thread(ask, document)


async def summarize_batch(documents: list[str], max_concurrency: int = 10) -> list[str]:
    """Summarize many documents concurrently, capped at max_concurrency."""
    semaphore = asyncio.Semaphore(max_concurrency)
    coroutines = [summarize_one(doc, semaphore) for doc in documents]
    return await asyncio.gather(*coroutines)
