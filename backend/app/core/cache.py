"""In-process TTL caches.

FDD specifies Redis-backed caches (introspection, authz decisions, throttle
windows) with the binding rule "cache is acceleration only, never authority".
The mandated stack (ARCHITECTURE.md) contains no Redis, so these are
process-local equivalents honoring the same TTLs and explicit-invalidation
contracts. Swapping in Redis later changes only this module.
"""
import time
from collections import deque
from threading import Lock
from typing import Any, Hashable


class TTLCache:
    def __init__(self, ttl_s: float, max_size: int = 10_000) -> None:
        self._ttl = ttl_s
        self._max = max_size
        self._data: dict[Hashable, tuple[float, Any]] = {}
        self._lock = Lock()

    def get(self, key: Hashable) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires, value = entry
            if expires < time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            if len(self._data) >= self._max:
                now = time.monotonic()
                self._data = {k: v for k, v in self._data.items() if v[0] >= now}
                while len(self._data) >= self._max:
                    self._data.pop(next(iter(self._data)))
            self._data[key] = (time.monotonic() + self._ttl, value)

    def delete(self, key: Hashable) -> None:
        with self._lock:
            self._data.pop(key, None)

    def delete_where(self, predicate) -> None:
        with self._lock:
            for k in [k for k in self._data if predicate(k)]:
                del self._data[k]

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class SlidingWindowCounter:
    """Sliding-window throttle counters (M01 T1/T2). Process-local; the
    durable security-critical limits (per-code attempts, per-email backoff)
    live in PostgreSQL per FDD §2.1.4."""

    def __init__(self) -> None:
        self._events: dict[Hashable, deque[float]] = {}
        self._lock = Lock()

    def hit_and_count(self, key: Hashable, window_s: float) -> int:
        now = time.monotonic()
        with self._lock:
            q = self._events.setdefault(key, deque())
            cutoff = now - window_s
            while q and q[0] < cutoff:
                q.popleft()
            q.append(now)
            return len(q)

    def count(self, key: Hashable, window_s: float) -> int:
        now = time.monotonic()
        with self._lock:
            q = self._events.get(key)
            if not q:
                return 0
            cutoff = now - window_s
            while q and q[0] < cutoff:
                q.popleft()
            return len(q)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()
