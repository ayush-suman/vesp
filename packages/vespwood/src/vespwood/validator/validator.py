import inspect
from abc import ABC, abstractmethod
from functools import partial
from typing import Callable, Protocol, ParamSpec, Generic, Awaitable, TypeAlias
from vespwood._format_object import to_format_object
from vespwood._utils import format_map
from vespwood.errors.validation_error import ValidationError
from vespwood.validator.validator_type import ValidatorType, ValidatorTypeOptions
from vespwood_generator.message import Message
from vespwood_generator.suppliment import Supplimentable

MergeFunc: TypeAlias = Callable[[Message, Message], Message]

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

    def __init__(self, name: str, description: str | None = None, validator_type: ValidatorType = ValidatorTypeOptions.DISCARD_ALL):
        self._name = name
        self._description = description
        self._content = validator_type.content
        self._params = validator_type.params
        self._merge_strategy = validator_type.merge_strategy
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

    async def __call__(self, messages: list[Message], response: Message, *args: I.args, **kwargs: I.kwargs) -> tuple[Message, MergeFunc] | None:
        try:
            task = self.validate(response, messages, *args, **kwargs)
            if task and inspect.isawaitable(task):
                await task
        except ValidationError as e:
            format_args = to_format_object(e.format_args)
            prompt_mapping = format_args.get_params(self._params or [])
            content = []
            for block in self._content:
                if isinstance(block, str):
                    block = format_map(block, prompt_mapping)
                content.append(block)
            message = Message("system", content)
            merge_func = partial(self._merge_strategy.__call__, e.invalid_blocks)
            return message, merge_func


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
    
