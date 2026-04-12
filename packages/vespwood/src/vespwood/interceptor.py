from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable
import inspect
from typing import Protocol, TypeAlias, overload
from vespwood_generator import (
    Tag, Response,
)
from vespwood.message import Prompt
from vespwood.types import HooksList, Saves, SchemaInfo, ToolsList, ValidatorsList
from vespwood.format_object import FormatKeys


class OnResponse(Protocol):
    def __call__(self, response: Response) -> None: ...


class AsyncOnResponse(Protocol):
    async def __call__(self, response: Response) -> None: ...


ResponseHandler: TypeAlias = OnResponse | AsyncOnResponse

NameSession: TypeAlias = Callable[[str, str | None, str | None], None]


class InterceptorFn(Protocol):
    def __call__(
        self,
        session_id: str,
        prompts: list[Prompt],
        format_keys: FormatKeys,
        tag: Tag,
        schema: SchemaInfo | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        saves: Saves | None = None,
    ) -> ResponseHandler | None: ...


class AsyncInterceptorFn(Protocol):
    async def __call__(
        self,
        session_id: str,
        prompts: list[Prompt],
        format_keys: FormatKeys,
        tag: Tag,
        schema: SchemaInfo | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        saves: Saves | None = None,
    ) -> ResponseHandler | None: ...


class Interceptor(ABC, InterceptorFn):
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
        prompts: list[Prompt],
        format_keys: FormatKeys,
        tag: Tag,
        schema: SchemaInfo | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        saves: Saves | None = None,
    ) -> ResponseHandler | None:
        ...

    def __call__(
        self,
        session_id: str,
        prompts: list[Prompt],
        format_keys: FormatKeys,
        tag: Tag,
        schema: SchemaInfo | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        saves: Saves | None = None,
    ) -> ResponseHandler | None:
        return self.intercept(
            session_id, prompts, format_keys, tag, schema, tools, hooks, validators, saves
        )


class AsyncInterceptor(ABC, AsyncInterceptorFn):
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
    async def intercept(
        self,
        session_id: str,
        prompts: list[Prompt],
        format_keys: FormatKeys,
        tag: Tag,
        schema: SchemaInfo | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        saves: Saves | None = None,
    ) -> ResponseHandler | None:
        ...

    async def __call__(
        self,
        session_id: str,
        prompts: list[Prompt],
        format_keys: FormatKeys,
        tag: Tag,
        schema: SchemaInfo | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        saves: Saves | None = None,
    ) -> ResponseHandler | None:
        return await self.intercept(
            session_id, prompts, format_keys, tag, schema, tools, hooks, validators, saves
        )


@overload
def interceptor(func: InterceptorFn, *, name_session: NameSession | None = None) -> Interceptor: ...


@overload
def interceptor(func: AsyncInterceptorFn, *, name_session: NameSession | None = None) -> AsyncInterceptor: ...


def interceptor(func: InterceptorFn | AsyncInterceptorFn, *, name_session: NameSession | None = None) -> Interceptor | AsyncInterceptor:
    def wrapper(fn: InterceptorFn | AsyncInterceptorFn):
        if inspect.iscoroutinefunction(fn):
            class Wrapper(AsyncInterceptor):
                def __init__(self):
                    if name_session: self.name_session(name_session)
                    super().__init__()

                async def intercept(
                    self,
                    session_id: str,
                    prompts: list[Prompt],
                    format_keys: FormatKeys,
                    tag: Tag,
                    schema: SchemaInfo | None = None,
                    tools: ToolsList | None = None,
                    hooks: HooksList | None = None,
                    validators: ValidatorsList | None = None,
                    saves: Saves | None = None,
                ) -> ResponseHandler | None:
                    return await fn( 
                        session_id,
                        prompts,
                        format_keys,
                        tag,
                        schema,
                        tools,
                        hooks,
                        validators,
                        saves,
                    )

        else:
            class Wrapper(Interceptor):
                def __init__(self):
                    if name_session: self.name_session(name_session)
                    super().__init__()

                def intercept(
                    self,
                    session_id: str,
                    prompts: list[Prompt],
                    format_keys: FormatKeys,
                    tag: Tag,
                    schema: SchemaInfo | None = None,
                    tools: ToolsList | None = None,
                    hooks: HooksList | None = None,
                    validators: ValidatorsList | None = None,
                    saves: Saves | None = None,
                ) -> ResponseHandler | None:
                    return fn( 
                        session_id,
                        prompts,
                        format_keys,
                        tag,
                        schema,
                        tools,
                        hooks,
                        validators,
                        saves,
                    )

        Wrapper.__name__ = func.__name__
        Wrapper.__qualname__ = func.__qualname__
        Wrapper.__module__ = func.__module__
        return Wrapper()
    if func: 
        return wrapper(func)
    return wrapper

