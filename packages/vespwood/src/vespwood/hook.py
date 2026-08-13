from abc import ABC, abstractmethod
import inspect
from typing import Any, Protocol, Generic, ParamSpec, Awaitable
from vespwood_generator import Message, Tool, Schematic, Supplimentable


I = ParamSpec('I')
class AsyncHookFn(Protocol, Generic[I]):
    async def __call__(message: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any]: 
        ...

class HookFn(Protocol, Generic[I]):
    def __call__(message: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any]: 
        ...

class Hook(Supplimentable["message"], ABC, Generic[I]):
    __slots__ = "_name", "_description"

    def __init__(self, name: str | None = None, description: str | None = None):
        self._name: str = name or self.__class__.__name__
        self._description: str | None = description or self.__class__.__doc__
        def stub(*args: I.args, **kwargs: I.kwargs): ...
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

    @abstractmethod
    def on_response(self, message: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any] | Awaitable[dict[str, Any] | None]: ...


    async def __call__(self, message: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any]:
        new_args = self.on_response(message, *args, **kwargs)
        if inspect.isawaitable(new_args):
            new_args = await new_args
        return new_args or {}


def hook(func: AsyncHookFn[I] | HookFn[I] | None = None, *, name: str | None = None, description: str | None = None) -> Hook[I]:
    def wrapper(fn: AsyncHookFn[I] | HookFn[I]):
        if inspect.iscoroutinefunction(fn):
            class Wrapper(Hook[I]):
                def __init__(self):
                    super().__init__(
                        name=name or fn.__name__, 
                        description=description or fn.__doc__
                    )

                async def on_response(self, latest_response: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any] | None:
                    return await fn(latest_response, *args, **kwargs)
        
            Wrapper.__class__.__qualname__ = fn.__class__.__qualname__
            Wrapper.__class__.__name__ = fn.__class__.__name__
            return Wrapper()
        else:
            class Wrapper(Hook[I]):
                def __init__(self):
                    super().__init__(
                        name=name or fn.__name__, 
                        description=description or fn.__doc__
                    )

                def on_response(self, latest_response: Message, *args: I.args, **kwargs: I.kwargs) -> dict[str, Any] | None:
                    return fn(latest_response, *args, **kwargs)
        
            Wrapper.__class__.__qualname__ = fn.__class__.__qualname__
            Wrapper.__class__.__name__ = fn.__class__.__name__
            return Wrapper()

    if func:
        wrapper.__qualname__ = func.__qualname__
        wrapper.__name__ = func.__name__
        return wrapper(func)
    return wrapper
    

