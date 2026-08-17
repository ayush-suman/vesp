from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable
import inspect
from typing import Protocol, TypeAlias, overload


class OnResponse(Protocol):
    def __call__(response: Response) -> None: ...

class AsyncOnResponse(Protocol):
    async def __call__(response: Response) -> None: ...

class ResponseHandler:
    def __init__(self, on_response: OnResponse | AsyncOnResponse):
        self.on_response = on_response

    async def __call__(self, response: Response):
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
        awaited_prompt: Prompt,
        schema: Schema | None
    ) -> ResponseHandler | None: ...

class AsyncInterceptorFn(Protocol):
    async def __call__(
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        awaited_prompt: Prompt,
        schema: Schema | None
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
        awaited_prompt: Prompt,
        schema: Schema | None
    ) -> ResponseHandler | None | Awaitable[ResponseHandler | None]:
        ...

    async def __call__(
        self,
        session_id: str,
        messages: list[Message],
        args: dict[str, Any],
        awaited_prompt: Prompt,
        schema: Schema | None
    ) -> ResponseHandler | None:
        on_response = self.intercept(session_id, messages, args, awaited_prompt)
        if on_response is not None:
            if inspect.isawaitable(on_response):
                on_response = await on_response
            return ResponseHandler(on_response)
        

def interceptor(func: InterceptorFn | AsyncInterceptorFn | None = None, *, name_session: NameSession | None = None) -> Interceptor:
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
                    awaited_prompt: Prompt,
                    schema: Schema | None
                ) -> ResponseHandler | None:
                    return await fn( 
                        session_id,
                        messages,
                        args,
                        awaited_prompt,
                        schema
                    )

        else:
            class Wrapper(Interceptor):
                def __init__(self):
                    if name_session: self.name_session(name_session)
                    super().__init__()

                def intercept(
                    self,
                    session_id: str,
                    messages: list[Message],
                    args: dict[str, Any],
                    awaited_prompt: Prompt,
                    schema: Schema | None
                ) -> ResponseHandler | None:
                    return fn( 
                        session_id,
                        prompts,
                        format_keys,
                        awaited_prompt,
                        schema
                    )

        Wrapper.__name__ = func.__name__
        Wrapper.__qualname__ = func.__qualname__
        Wrapper.__module__ = func.__module__
        return Wrapper()
    if func: 
        return wrapper(func)
    return wrapper

