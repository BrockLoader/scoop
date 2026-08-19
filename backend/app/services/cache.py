"""In-process TTL cache for search results.

Key shape: `(retailer_slug, normalised_query, postcode, volume_ml_bucket)`.
We do NOT introduce Redis for the POC — this in-memory cache is fine
for a single-process FastAPI instance.

The brief calls out a 1800-second (30 min) TTL. Cache key includes
volume only when it materially changes the request — currently it
doesn't (we don't filter by volume on the upstream call), so the
volume component is informational rather than load-bearing.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from ..scrapers.base import RawProduct


@dataclass
class CacheEntry:
    value: list[RawProduct]
    expires_at: float


class SearchCache:
    def __init__(self, ttl_seconds: int = 1800) -> None:
        self._ttl = ttl_seconds
        self._store: dict[tuple, CacheEntry] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def make_key(
        retailer: str,
        normalized_query: str,
        postcode: Optional[str],
    ) -> tuple:
        return (retailer, normalized_query, postcode or "")

    async def get(self, key: tuple) -> Optional[list[RawProduct]]:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            if entry.expires_at < time.time():
                self._store.pop(key, None)
                return None
            return list(entry.value)

    async def set(self, key: tuple, value: list[RawProduct]) -> None:
        async with self._lock:
            self._store[key] = CacheEntry(
                value=list(value), expires_at=time.time() + self._ttl
            )

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()