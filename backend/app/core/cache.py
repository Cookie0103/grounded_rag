"""内存缓存：LRU 淘汰 + TTL 过期。单进程使用，不做并发加锁（协程之间没有 await 点）。"""

import time
from collections import OrderedDict
from collections.abc import Callable


class TtlCache[K, V]:
    def __init__(
        self,
        max_size: int,
        ttl_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._clock = clock
        self._items: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: K) -> V | None:
        entry = self._items.get(key)
        if entry is None or self._clock() - entry[0] > self._ttl:
            self._items.pop(key, None)
            self.misses += 1
            return None
        self._items.move_to_end(key)
        self.hits += 1
        return entry[1]

    def put(self, key: K, value: V) -> None:
        self._items[key] = (self._clock(), value)
        self._items.move_to_end(key)
        while len(self._items) > self._max_size:
            self._items.popitem(last=False)

    def __len__(self) -> int:
        return len(self._items)
