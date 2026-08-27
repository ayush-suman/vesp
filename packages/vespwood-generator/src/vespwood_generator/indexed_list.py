from __future__ import annotations
from typing import Callable, TypeVar, Generic
import bisect


T = TypeVar("T")
K = TypeVar("K")
class IndexedList(list[T], Generic[T, K]):
    def __init__(self, iterable: list[T] = [], key: Callable[[T], K] | None = None):
        iterable.sort(key=key) if key else iterable.sort()
        self._key = key
        super().__init__(iterable)

    def find(self, value: K) -> T | None:
        i = bisect.bisect_left(self, value, key=self._key)
        if i == len(self) or self._key(self[i]) != value:
            return None
        return self[i]

    def insert(self, item: T):
        i = bisect.bisect_left(self, self._key(item), key=self._key)
        super().insert(i, item)

    def __contains__(self, item: T) -> bool:
        item = self.find(self._key(item))
        return item is not None

    def __add__(self, iter: list[T]) -> IndexedList[T, K]:
        new = IndexedList(self.copy(), key=self._key)
        for i in iter:
            new.insert(i)
        return new