from abc import ABC, abstractmethod
from typing import Protocol, Any
from vespwood_generator.message import Message, Response


class ValidatorFn(Protocol):
    def __call__(self, prompts: list[Message], response: Response, format_keys: dict[str, Any]):
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
    def validate(self, prompts: list[Message], response: Response, format_keys: dict[str, Any]):
        ...

    def __call__(self, prompts: list[Message], response: Response, format_keys: dict[str, Any]):
        return self.validate(response, prompts, format_keys)


def validator(func: ValidatorFn | None = None, *, name: str | None = None, description: str | None = None):
    def wrapper(fn: ValidatorFn):
        class Wrapper(Validator):
            def __init__(self):
                self._name = name or fn.__name__
                self._description = description or fn.__doc__
                super().__init__()

            def validate(self, prompts: list[Message], response: Response, format_keys: dict[str, Any]):
                return fn(prompts, response, format_keys)
    
        Wrapper.__class__.__qualname__ = Validator.__class__.__qualname__
        Wrapper.__class__.__name__ = Validator.__class__.__name__
        return Wrapper()
    
    wrapper.__qualname__ = func.__qualname__
    wrapper.__name__ = func.__name__
    return wrapper(func) if func else wrapper
    

