from abc import abstractmethod
import inspect
from typing import Any, Callable, Concatenate, Generic, ParamSpec, TypeVar, Awaitable
from vespwood_generator import Schematic, Tool, Supplimentable, suppliment
from vespwood_generator.message import Message
from .hook import Hook


I = ParamSpec("I")
O = TypeVar("O")

class HookTool(Tool[Concatenate[Message, I], tuple[dict[str, Any], O]], Supplimentable["message"], Generic[I, O]):
    def __init__(self, hook: Hook, schema: Schematic | None = None, name: str | None = None, description: str | None = None):
        super().__init__(name or hook.name, description or hook.description, schema or hook.schema)
        self._hook = hook

    @abstractmethod
    def tool_result(self, **kwargs) -> O | Awaitable[O]: ...

    async def __call__(self, message: Message, *args: I.args, **kwds: I.kwargs) -> tuple[dict[str, Any], O]:
        returned_args = await self._hook(message, *args, **kwds)
        tool_result = suppliment(self.tool_result, **returned_args)
        result = tool_result()
        if inspect.isawaitable(result):
            result = await result
        return returned_args, result


def hooktool(func: Callable[[dict[str, Any]], O] | None = None, *, hook: Hook[I], schema: Schematic, name: str | None = None, description: str | None = None):
    def wrapper(fn: Callable[[dict[str, Any]], O]):
        class Wrapper(HookTool[I, O]):
            def tool_result(self, returned_args):
                return fn(returned_args)

        Wrapper.__class__.__qualname__ = fn.__class__.__qualname__
        Wrapper.__class__.__name__ = fn.__class__.__name__
        return Wrapper(hook=hook, schema=schema, name=name, description=description)

    if func:
        wrapper.__qualname__ = func.__qualname__
        wrapper.__name__ = func.__name__
        return wrapper(func)
    return wrapper
    

        


        