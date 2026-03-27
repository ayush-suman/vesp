from abc import ABC, abstractmethod
from typing import Any, Protocol
from vespwood.message import Response
from vespwood.tagged_messages import TaggedMessages


class HookFn(Protocol):
    def __call__(self, latest_response: Response, messages: TaggedMessages, format_keys: dict[str, Any], **kwargs) -> dict[str, Any] | None: 
        ...


class Hook(HookFn, ABC):
    __slots__ = "_name", "_description"
    
    _name: str
    _description: str | None

    @property
    def name(self):
        return self._name
    
    @property
    def description(self):
        return self._description

    @abstractmethod
    def on_response(self, latest_response: Response, messages: TaggedMessages, format_keys: dict[str, Any], **kwargs) -> dict[str, Any] | None:
        pass

    def __call__(self, latest_response, responses, format_keys, **kwargs):
        return self.on_response(latest_response, responses, format_keys, **kwargs)


def hook(func: HookFn | None = None, *, name: str | None = None, description: str | None = None):
    def wrapper(fn: HookFn):
        class Wrapper(Hook):
            def __init__(self):
                self._name = name or fn.__name__
                self._description = description or fn.__doc__
                super().__init__()

            def on_response(self, latest_response: Response, messages: TaggedMessages, format_keys: dict[str, Any], **kwargs) -> dict[str, Any] | None:
                return fn(latest_response, messages, format_keys, **kwargs)
    
        Wrapper.__class__.__qualname__ = fn.__class__.__qualname__
        Wrapper.__class__.__name__ = fn.__class__.__name__
        return Wrapper()
    
    wrapper.__qualname__ = func.__qualname__
    wrapper.__name__ = func.__name__
    return wrapper(func) if func else wrapper
    

