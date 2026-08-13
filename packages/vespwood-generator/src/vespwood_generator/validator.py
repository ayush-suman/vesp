import inspect
from abc import ABC, abstractmethod
from typing import Protocol, Any, ParamSpec, Generic, Awaitable
from vespwood_generator.message import Message
from vespwood_generator.suppliment import Supplimentable

I = ParamSpec("I")
class ValidatorFn(Protocol, Generic[I]):
    def __call__(messages: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs):
        ...

class AsyncValidatorFn(Protocol, Generic[I]):
    async def __call__(messages: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs):
        ...

class Validator(Supplimentable["messages", "response"], ABC, Generic[I]):
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
    def validate(self, messages: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs) -> None | Awaitable[None]:
        ...

    async def __call__(self, messages: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs):
        task = self.validate(response, messages, *args, **kwargs)
        if task and inspect.isawaitable(task):
            await task


def validator(func: ValidatorFn[I] | AsyncValidatorFn[I] | None = None, *, name: str | None = None, description: str | None = None):
    def wrapper(fn: ValidatorFn[I] | AsyncValidatorFn[I]) -> Validator[I]:
        if inspect.iscoroutinefunction(fn):
            class Wrapper(Validator[I]):
                def __init__(self):
                    self._name = name or fn.__name__
                    self._description = description or fn.__doc__
                    super().__init__()

                async def validate(self, prompts: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs):
                    return await fn(prompts, response, *args, **kwargs)
        
            Wrapper.__class__.__qualname__ = Validator.__class__.__qualname__
            Wrapper.__class__.__name__ = Validator.__class__.__name__
            return Wrapper()
        else:
            class Wrapper(Validator[I]):
                def __init__(self):
                    self._name = name or fn.__name__
                    self._description = description or fn.__doc__
                    super().__init__()

                def validate(self, prompts: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs):
                    return fn(prompts, response, *args, **kwargs)
        
            Wrapper.__class__.__qualname__ = Validator.__class__.__qualname__
            Wrapper.__class__.__name__ = Validator.__class__.__name__
            return Wrapper()
    
    wrapper.__qualname__ = func.__qualname__
    wrapper.__name__ = func.__name__
    return wrapper(func) if func else wrapper
    

