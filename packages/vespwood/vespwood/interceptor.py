from abc import ABC, abstractmethod
from typing import Any, Protocol, overload
from vespwood.message import Prompt, Response
from vespwood.types.hooks_list import HooksList
from vespwood.types.saves import Saves
from vespwood.types.schema_info import SchemaInfo
from vespwood.types.tools_list import ToolsList
from vespwood.types.validators_list import ValidatorsList
from vespwood.tag import Tag


class OnResponse(Protocol):
    @overload
    def __call__(self, response: Response):
        ...

    @overload
    def __call__(self, response: Response):
        ...


class InterceptorFn(Protocol):
    @overload
    async def __call__(self, prompts: list[Prompt], tag: Tag, schema: SchemaInfo | None = None, tools: ToolsList | None = None, hooks: HooksList | None = None, validators: ValidatorsList | None = None, saves: Saves | None = None, format_keys: dict[str, Any] = {}) -> OnResponse | None:
        ...

    @overload
    def __call__(self, prompts: list[Prompt], tag: Tag, schema: SchemaInfo | None = None, tools: ToolsList | None = None, hooks: HooksList | None = None, validators: ValidatorsList | None = None, saves: Saves | None = None, format_keys: dict[str, Any] = {}) -> OnResponse | None:
        ...


class Interceptor(ABC, InterceptorFn):
    @abstractmethod
    def intercept(self, prompts: list[Prompt], tag: Tag, schema: SchemaInfo | None = None, tools: ToolsList | None = None, hooks: HooksList | None = None, validators: ValidatorsList | None = None, saves: Saves | None = None, format_keys: dict[str, Any] = {}) -> OnResponse | None:
        ...

    def __call__(self, prompts: list[Prompt], tag: Tag, schema: SchemaInfo | None = None, tools: ToolsList | None = None, hooks: HooksList | None = None, validators: ValidatorsList | None = None, saves: Saves | None = None, format_keys: dict[str, Any] = {}) -> OnResponse | None:
        return self.intercept(prompts, tag, schema, tools, hooks, validators, saves, format_keys)
    

def interceptor(func: InterceptorFn):
    def wrapper(fn: InterceptorFn):
        class Wrapper(Interceptor):
            def intercept(self, prompts, tag, schema = None, tools = None, hooks = None, validators = None, saves = None, format_keys = {}) -> OnResponse | None:
                return fn(prompts, tag, schema, tools, hooks, validators, saves, format_keys)
        
        Wrapper.__class__.__qualname__ = fn.__qualname__
        Wrapper.__class__.__name__ = fn.__name__
        return Wrapper()
    wrapper.__qualname__ = func.__qualname__
    wrapper.__name__ = func.__name__
    return wrapper(func) if func else wrapper
            

