"""Size + linger batching for the worker.

Generic over item type — the consumer feeds in decoded ClickEvent
instances. The batcher just decides when to flush and what to flush.
"""

from __future__ import annotations

import time
from typing import Generic, TypeVar

T = TypeVar("T")


class Batcher(Generic[T]):
    def __init__(self, max_size: int, max_linger_seconds: float) -> None:
        self._max_size = max_size
        self._max_linger_seconds = max_linger_seconds
        self._buffer: list[T] = []
        self._first_added_at: float | None = None

    def add(self, item: T) -> None:
        if not self._buffer:
            self._first_added_at = time.monotonic()
        self._buffer.append(item)

    def should_flush(self) -> bool:
        if not self._buffer:
            return False
        if len(self._buffer) >= self._max_size:
            return True
        assert self._first_added_at is not None
        return (time.monotonic() - self._first_added_at) >= self._max_linger_seconds

    def drain(self) -> list[T]:
        items = self._buffer
        self._buffer = []
        self._first_added_at = None
        return items

    def __len__(self) -> int:
        return len(self._buffer)
