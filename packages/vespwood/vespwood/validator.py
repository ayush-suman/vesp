from abc import ABC, abstractmethod
from typing import Any, Protocol
from vespwood.message import Response
from vespwood.tagged_messages import TaggedMessages


class ValidatorFn(Protocol):
    def __call__(self, latest_response: Response, messages: TaggedMessages, format_keys: dict[str, Any]):
        ...


class Validator(ABC, ValidatorFn):
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
    def validate(self, latest_response: Response, messages: TaggedMessages, format_keys: dict[str, Any]):
        ...

    def __call__(self, latest_response: Response, messages: TaggedMessages, format_keys: dict[str, Any]):
        return self.validate(latest_response, messages, format_keys)


def validator(func: ValidatorFn | None = None, *, name: str | None = None, description: str | None = None):
    def wrapper(fn: ValidatorFn):
        class Wrapper(Validator):
            def __init__(self):
                self._name = name or fn.__name__
                self._description = description or fn.__doc__
                super().__init__()

            def validate(self, latest_response: Response, messages: TaggedMessages, format_keys: dict[str, Any]):
                return fn(latest_response, messages, format_keys)
    
        Wrapper.__class__.__qualname__ = Validator.__class__.__qualname__
        Wrapper.__class__.__name__ = Validator.__class__.__name__
        return Wrapper()
    
    wrapper.__qualname__ = func.__qualname__
    wrapper.__name__ = func.__name__
    return wrapper(func) if func else wrapper
    

