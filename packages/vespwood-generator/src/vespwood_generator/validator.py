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

class Validator(ABC, Generic[I], Supplimentable["messages", "response"]):
    __slots__ = "_name", "_description"

    _name: str
    _description: str | None

    def __init__(self, name: str, description: str | None = None):
        self._name = name
        self._description = description
        if not self.params_inferred: self.infer_params_from(self.validate)

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
        class Wrapper(Validator[I]):
            def __init__(self):
                self.infer_params_from(fn)
                super().__init__(
                    name or fn.__name__, 
                    description or fn.__doc__
                )

            def validate(self, messages: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs) -> None | Awaitable[None]:
                return fn(messages, response, *args, **kwargs)
    
        Wrapper.__class__.__qualname__ = Validator.__class__.__qualname__
        Wrapper.__class__.__name__ = Validator.__class__.__name__
        return Wrapper()
    
    wrapper.__qualname__ = func.__qualname__
    wrapper.__name__ = func.__name__
    return wrapper(func) if func else wrapper
    

