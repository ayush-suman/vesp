from __future__ import annotations
from typing import Callable, TypeVar, Generic
import bisect


T = TypeVar("T")
K = TypeVar("K")
class IndexedList(list[T], Generic[T, K]):
    def __init__(self, iterable: list[T] = [], key: Callable[[T], K] | None = None):
        self._key_index: dict[K, T] = {}
        for item in iterable:
            self._key_index[key(item) if key else item] = item
        self._key = key or (lambda x: x)
        super().__init__(iterable)

    def find(self, value: K) -> T | None:
        return self._key_index.get(value, None)

    def insert(self, item: T):
        self._key_index[self._key(item)] = item
        super().append(item)

    def append(self, item: T):
        self._key_index[self._key(item)] = item
        super().append(item)

    def remove(self, item: T):
        key = self._key(item)
        if key in self._key_index:
            del self._key_index[key]
        super().remove(item)

    def __contains__(self, item: T) -> bool:
        i = self._key_index.get(self._key(item), None)
        if i is None or i != item:
            return False
        return True

    def __add__(self, iter: list[T]) -> IndexedList[T, K]:
        new = self.copy()
        new._key_index.update({self._key(i): i for i in iter})
        new.extend(iter)
        return new

    def __len__(self):
        return len(self._key_index)

    def copy(self) -> IndexedList[T, K]:
        return IndexedList(list(self), key=self._key)
