from abc import ABC, abstractmethod
import inspect
from typing import Protocol, TypeAlias, overload
from vespwood_generator import (
    Tag, Prompt, Response,
    HooksList, Saves, SchemaInfo, ToolsList, ValidatorsList
)
from vespwood.format_object import FormatKeys


class OnResponse(Protocol):
    def __call__(self, response: Response) -> None: ...


class AsyncOnResponse(Protocol):
    async def __call__(self, response: Response) -> None: ...


ResponseHandler: TypeAlias = OnResponse | AsyncOnResponse


class InterceptorFn(Protocol):
    def __call__(
        self,
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
    @abstractmethod
    def intercept(
        self,
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
            prompts, format_keys, tag, schema, tools, hooks, validators, saves
        )


class AsyncInterceptor(ABC, AsyncInterceptorFn):
    @abstractmethod
    async def intercept(
        self,
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
            prompts, format_keys, tag, schema, tools, hooks, validators, saves
        )


@overload
def interceptor(func: InterceptorFn) -> Interceptor: ...


@overload
def interceptor(func: AsyncInterceptorFn) -> AsyncInterceptor: ...


def interceptor(func: InterceptorFn | AsyncInterceptorFn) -> Interceptor | AsyncInterceptor:
    if inspect.iscoroutinefunction(func):
        class Wrapper(AsyncInterceptor):
            async def intercept(
                self,
                prompts: list[Prompt],
                format_keys: FormatKeys,
                tag: Tag,
                schema: SchemaInfo | None = None,
                tools: ToolsList | None = None,
                hooks: HooksList | None = None,
                validators: ValidatorsList | None = None,
                saves: Saves | None = None,
            ) -> ResponseHandler | None:
                return await func( 
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
            def intercept(
                self,
                prompts: list[Prompt],
                format_keys: FormatKeys,
                tag: Tag,
                schema: SchemaInfo | None = None,
                tools: ToolsList | None = None,
                hooks: HooksList | None = None,
                validators: ValidatorsList | None = None,
                saves: Saves | None = None,
            ) -> ResponseHandler | None:
                return func( 
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

