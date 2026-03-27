from abc import ABC, abstractmethod

from .caller import Caller

from vespwood.schematic import Tool

# TODO: Change impl
# TODO: Create Lazy Schematic, Lazy Invokable and Lazy Tool for this
# TODO: __iter__ should return without schema
# TODO: __call__ should return invokable tool with schema
class ToolCaller(Caller[Tool], ABC):
    def __init__(self, names: list[str]):
        self._names = names
        super().__init__()


    def __iter__(self):
        return iter(map(lambda n: self(n), self._names))
    
    
    @abstractmethod
    def __call__(self, name: str) -> Tool:
        ...


def tool_caller(names: list[str]):
    def wrapper(func: Caller):
        class Wrapper(ToolCaller):
            def __init__(self, names: list[str]):
                super().__init__(names)

            def __call__(self, name):
                return func(name)
        
        
        Wrapper.__name__ = func.__name__
        Wrapper.__qualname__ = func.__qualname__
        return Wrapper(names)
    return wrapper