from abc import ABC, abstractmethod
import inspect
from typing import Any, Protocol, Generic, ParamSpec
from vespwood_generator import Message, Tool, Schematic


I = ParamSpec('I')
class HookFn(Protocol, Generic[I]):
    async def __call__(self, latest_response: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any]: 
        ...

class Hook(HookFn[I], ABC, Generic[I]):
    __slots__ = "_name", "_description"

    def __init__(self, name: str | None = None, description: str | None = None):
        self._name: str = name or self.__class__.__name__
        self._description: str | None = description or self.__class__.__doc__
        def stub(*args: I.args, *kwargs: I.kwargs): ...
        self._schema: Schematic = Schematic.to_json_schema(stub)

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str | None:
        return self._description

    @property
    def schema(self) -> Schematic:
        return self._schema

    @overload
    def on_response(self, latest_response: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any] | None: ...
    @overload
    def on_response(self, latest_response: Message, *args: I.args, **kwargs: I.kwargs) -> Awaitable[dict[str, Any] | None]: ...
    @abstractmethod
    def on_response(self, latest_response: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any] | Awaitable[dict[str, Any] | None]: ...


    async def __call__(self, latest_response, *args: I.args, **kwargs: I.kwargs) -> O:
        if inspect.iscoroutinefunction(self.on_response):
            return await self.on_response(latest_response, *args, **kwargs) or {}
        else:
            return self.on_response(latest_response, *args, **kwargs) or {}


def hook(func: HookFn[I] | None = None, *, name: str | None = None, description: str | None = None) -> Hook[I]:
    def wrapper(fn: HookFn[I]):
        class Wrapper(Hook[I]):
            def __init__(self):
                super().__init__(
                    name=name or fn.__name__, 
                    description=description or fn.__doc__
                )

            def on_response(self, latest_response: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any] | Awaitable[dict[str, Any]] | None:
                return fn(latest_response, *args, **kwargs)
    
        Wrapper.__class__.__qualname__ = fn.__class__.__qualname__
        Wrapper.__class__.__name__ = fn.__class__.__name__
        return Wrapper()

    if func:
        wrapper.__qualname__ = func.__qualname__
        wrapper.__name__ = func.__name__
        return wrapper(func)
    return wrapper
    

