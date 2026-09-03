from abc import abstractmethod
import inspect
from typing import Any, Callable, Generic, ParamSpec, TypeVar, Awaitable
from vespwood_generator import  Schematic, Tool, suppliment
from vespwood_generator.message import Message
from ..hook import Hook


I = ParamSpec("I")
O = TypeVar("O")
H = ParamSpec("H")
class HookTool(Tool[I, O], Generic[I, O, H]):
    def __init__(self, hook: Hook[H], name: str | None = None, description: str | None = None, schema: Schematic | None = None, ):
        self._hook = hook
        super().__init__(name, description, schema)

    @property
    def hook(self) -> Hook[H]:
        return self._hook


def hooktool(hook: Hook[H], *, name: str | None = None, description: str | None = None, schema: Schematic | None = None):
    def wrapper(fn: Callable[I, O]):
        class WrapperTool(HookTool[I, O, H]):
            __call__ = fn

        WrapperTool.__class__.__qualname__ = fn.__qualname__
        WrapperTool.__class__.__name__ = fn.__name__
        return WrapperTool(hook=hook, name=name or fn.__name__, description=description or fn.__doc__, schema=schema)
    return wrapper
    



        


        