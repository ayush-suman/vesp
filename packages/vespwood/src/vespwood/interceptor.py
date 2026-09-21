from abc import ABC, abstractmethod
import inspect
from typing import Protocol, TypeAlias, Callable, Awaitable, Any
from vespwood.hook import Hook
from vespwood_generator import Message
from vespwood_generator.blocks.block import Block
from vespwood_generator.schematic.schema import Schema
from vespwood_generator.schematic.tool import Tool
from vespwood_generator.validator import Validator


OnSessionStart: TypeAlias = Callable[[str, str | None, str | None], None]
OnResponse: TypeAlias = Callable[[str, str, Message], None]
OnValidationError: TypeAlias = Callable[[str, str, Validator, Message, list[Block]], None]

class InterceptorFn(Protocol):
    def __call__(
        session_id: str,
        prompt_id: str,
        messages: list[Message],
        args: dict[str, Any],
        schema: Schema | None = None, 
        tools: list[Tool] = [],
        hooks: list[Hook] = [],
        validators: list[Validator] = [],
        saves: dict[str, str] | None = None,
        tag: str | None = None
    ) -> None: ...

class AsyncInterceptorFn(Protocol):
    async def __call__(
        session_id: str,
        prompt_id: str,
        messages: list[Message],
        args: dict[str, Any],
        schema: Schema | None = None, 
        tools: list[Tool] = [],
        hooks: list[Hook] = [],
        validators: list[Validator] = [],
        saves: dict[str, str] | None = None,
        tag: str | None = None
    ) -> None: ...

class Interceptor(ABC):
    _on_session_start_callback: OnSessionStart | None = None
    _on_validation_error_callback: OnValidationError | None = None
    _on_response_callback: OnResponse | None = None

    def on_session_start(self, function: OnSessionStart):
        self._on_session_start_callback = function
        return function

    def on_response(self, function: OnResponse):
        self._on_response_callback = function
        return function

    def on_validation_error(self, function: OnValidationError):
        self._on_validation_error_callback = function
        return function

    async def on_session_start_callback(self, session_id: str, name: str | None, description: str | None = None):
        if func := self._on_session_start_callback:
            if inspect.iscoroutinefunction(func):
                await func(session_id, name, description)
            else: 
                func(session_id, name, description)


    async def on_response_callback(self, session_id: str, prompt_id: str, response: Message):
        if func := self._on_response_callback:
            if inspect.iscoroutinefunction(func):
                await func(session_id, prompt_id, response)
            else: 
                func(session_id, prompt_id, response)


    async def on_validation_error_callback(self, session_id: str, prompt_id: str, validator: Validator, response: Message, error_content: list[Block]):
        if func := self._on_validation_error_callback:
            if inspect.iscoroutinefunction(func):
                await func(session_id, prompt_id, validator, response, error_content)
            else: 
                func(session_id, prompt_id, validator, response, error_content)
            
   
    @abstractmethod
    def intercept(
        self,
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        schema: Schema | None = None, 
        tools: list[Tool] = [],
        hooks: list[Hook] = [],
        validators: list[Validator] = [],
        saves: dict[str, str] | None = None,
        tag: str | None = None
    ) -> Awaitable[None] | None:
        ...

    async def __call__(
        self,
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        schema: Schema | None = None, 
        tools: list[Tool] = [],
        hooks: list[Hook] = [],
        validators: list[Validator] = [],
        saves: dict[str, str] | None = None,
        tag: str | None = None
    ) -> None:
        result = self.intercept(session_id, messages, args, schema, tools, hooks, validators, saves, tag)
        if inspect.isawaitable(result):
            result = await result
        

def interceptor(func: InterceptorFn | AsyncInterceptorFn | None = None, *, name_session: OnSessionStart | None = None) -> Interceptor:
    def wrapper(fn: InterceptorFn | AsyncInterceptorFn):
        class Wrapper(Interceptor):
            def __init__(self):
                if name_session: self.on_session_start(name_session)
                super().__init__()

            def intercept(
                self,
                session_id: str,
                prompt_id: str,
                messages: list[Message],
                args: dict[str, Any],
                schema: Schema | None = None, 
                tools: list[Tool] = [],
                hooks: list[Hook] = [],
                validators: list[Validator] = [],
                saves: dict[str, str] | None = None,
                tag: str | None = None
            ) -> Awaitable[None] | None:
                return fn( 
                    session_id,
                    prompt_id,
                    messages,
                    args,
                    schema,
                    tools,
                    hooks,
                    validators,
                    saves,
                    tag
                )
        Wrapper.__name__ = func.__name__
        Wrapper.__qualname__ = func.__qualname__
        Wrapper.__module__ = func.__module__
        return Wrapper()

    if func: 
        return wrapper(func)
    return wrapper

