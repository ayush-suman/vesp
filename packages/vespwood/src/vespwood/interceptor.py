from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable
import inspect
from typing import Protocol, TypeAlias, overload
from vespwood.message import Prompt


class OnResponse(Protocol):
    def __call__(self, response: Response) -> None: ...

class AsyncOnResponse(Protocol):
    async def __call__(self, response: Response) -> None: ...

ResponseHandler: TypeAlias = OnResponse | AsyncOnResponse

NameSession: TypeAlias = Callable[[str, str | None, str | None], None]

class InterceptorFn(Protocol):
    asyn def __call__(
        self,
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        awaited_prompt: Prompt | None
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
            
    @overload
    def intercept(
        self, 
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        awaited_prompt: Prompt | None
    ) -> ResponseHandler | None: ...
    @overload
    async def intercept(
        self, 
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        awaited_prompt: Prompt | None
    ) -> Awaitable[ResponseHandler | None]: ...
    @abstractmethod
    def intercept(
        self,
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        awaited_prompt: Prompt | None,
    ) -> ResponseHandler | Awaitable[ResponseHandler | None]:
        ...

    async def __call__(
        self,
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        awaited_prompt: Prompt | None
    ) -> ResponseHandler | None:
        if inspect.iscoroutinefunction(self.intercept):
            return await self.intercept(
                session_id, messages, args, awaited_prompt
            )
        else:
            return self.intercept(
                session_id, messages, args, awaited_prompt
            )


@overload
def interceptor(func: InterceptorFn, *, name_session: NameSession | None = None) -> Interceptor: ...
@overload
def interceptor(func: AsyncInterceptorFn, *, name_session: NameSession | None = None) -> Interceptor: ...
def interceptor(func: InterceptorFn | AsyncInterceptorFn, *, name_session: NameSession | None = None) -> Interceptor:
    def wrapper(fn: InterceptorFn | AsyncInterceptorFn):
        if inspect.iscoroutinefunction(fn):
            class Wrapper(Interceptor):
                def __init__(self):
                    if name_session: self.name_session(name_session)
                    super().__init__()

                async def intercept(
                    self,
                    session_id: str,
                    messages: list[Message],
                    args: dict[str, Any],
                    awaited_prompt: Prompt | None
                ) -> ResponseHandler | None:
                    return await fn( 
                        session_id,
                        messages,
                        args,
                        awaited_prompt,
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
                    format_keys: dict,
                    awaited_prompt: Prompt | None
                ) -> ResponseHandler | None:
                    return fn( 
                        session_id,
                        prompts,
                        format_keys,
                        awaited_prompt
                    )

        Wrapper.__name__ = func.__name__
        Wrapper.__qualname__ = func.__qualname__
        Wrapper.__module__ = func.__module__
        return Wrapper()
    if func: 
        return wrapper(func)
    return wrapper

