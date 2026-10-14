
from abc import ABC, abstractmethod
from typing import Callable

from vespwood.types.params import Params
from vespwood_generator.blocks.block import Block
from vespwood_generator.message import Message


class MergeStrategy(ABC):
    @abstractmethod
    def prune(self, invalid_blocks: list[Block], merged_message: Message) -> Message:
        ...

    @abstractmethod
    def update(self, pruned_message: Message, response: Message) -> Message:
        ...

    def __call__(self, invalid_blocks: list[Block], merged_message: Message, response: Message) -> Message:
        pruned_message = self.prune(invalid_blocks, merged_message)
        return self.update(pruned_message, response)


class _MergeStrategy(MergeStrategy):
    def __init__(self, update_func: Callable[[Message, Message], Message]):
        self._update_func = update_func

    def update(self, pruned_message, response):
        return self._update_func(pruned_message, response)

    def on_update(self, func: Callable[[Message, Message], Message]):
        self._update_func = func
    

def merge_strategy(func: Callable[[list[Block], Message], Message] | None = None):
    def wrapper(fn: Callable[[list[Block], Message], Message]):
        class Wrapper(_MergeStrategy):
            def prune(self, invalid_blocks, merged_message):
                return fn(invalid_blocks, merged_message)

        Wrapper.__name__ = fn.__name__
        Wrapper.__qualname__ = fn.__qualname__
        Wrapper.__module__ = fn.__module__

        return Wrapper(lambda m, r: Message(r.role, m.content + r.content))
    if func:
        return wrapper(func)
    return wrapper