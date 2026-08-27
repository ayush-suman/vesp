from abc import ABC, abstractmethod
import inspect
from typing import Protocol, TypeAlias, Callable, Awaitable, Any
from vespwood.hook import Hook
from vespwood_generator import Message
from vespwood_generator.schematic.schema import Schema
from vespwood_generator.schematic.tool import Tool
from vespwood_generator.validator import Validator


class OnResponse(Protocol):
    def __call__(response: Message) -> None: ...

class AsyncOnResponse(Protocol):
    async def __call__(response: Message) -> None: ...

class ResponseHandler:
    def __init__(self, on_response: OnResponse | AsyncOnResponse):
        self.on_response = on_response

    async def __call__(self, response: Message):
        if inspect.iscoroutinefunction(self.on_response):
            return await self.on_response(response)
        else:
            return self.on_response(response)


NameSession: TypeAlias = Callable[[str, str | None, str | None], None]

class InterceptorFn(Protocol):
    def __call__(
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        schema: Schema | None = None, 
        tools: list[Tool] = [],
        hooks: list[Hook] = [],
        validators: list[Validator] = [],
        saves: dict[str, str] | None = None,
        tag: str | None = None
    ) -> ResponseHandler | None: ...

class AsyncInterceptorFn(Protocol):
    async def __call__(
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        schema: Schema | None = None, 
        tools: list[Tool] = [],
        hooks: list[Hook] = [],
        validators: list[Validator] = [],
        saves: dict[str, str] | None = None,
        tag: str | None = None
    ) -> ResponseHandler | None: ...

class Interceptor(ABC):
    __bind_name_with_session: NameSession | None = None

    def name_session(self, function: NameSession):
        self.__bind_name_with_session = function
        return function

    async def bind_name_with_session(self, id: str, name: str | None, description: str | None = None):
        if func := self.__bind_name_with_session:
            if inspect.iscoroutinefunction(func):
                await func(id, name, description)
            else: 
                func(id, name, description)
            
   
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
    ) -> ResponseHandler | None | Awaitable[ResponseHandler | None]:
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
    ) -> ResponseHandler | None:
        on_response = self.intercept(session_id, messages, args, schema, tools, hooks, validators, saves, tag)
        if on_response is not None:
            if inspect.isawaitable(on_response):
                on_response = await on_response
            return ResponseHandler(on_response)
        

def interceptor(func: InterceptorFn | AsyncInterceptorFn | None = None, *, name_session: NameSession | None = None) -> Interceptor:
    def wrapper(fn: InterceptorFn | AsyncInterceptorFn):
        class Wrapper(Interceptor):
            def __init__(self):
                if name_session: self.name_session(name_session)
                super().__init__()

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
            ) -> ResponseHandler | None:
                return fn( 
                    session_id,
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

