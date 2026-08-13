import asyncio
import inspect
from typing import (
    Awaitable,
    Iterable,
    ParamSpec, 
    TypeVar, 
    Callable, 
    Concatenate, 
    Any,
    overload
)


from vesp.invokation import Invokation

from .agent import Agent


I = ParamSpec("I")
O = TypeVar("O")
def returns_args(func: Callable[Concatenate[Agent[I, O], I], dict[str, Any] | Iterable[dict[str, Any]] | Awaitable[dict[str, Any] | Iterable[dict[str, Any]]]] | None = None)  -> Callable[Concatenate[Agent[I, O], I], Invokation[O]]:
    def fn(self: Agent[I, O], *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        chain = Invokation()
        async def run_with():
            completion_futures: list[asyncio.Future] = []
            # Step 1: Prepare Args
            args_list = func(self, *args, **kwargs)
            if inspect.isawaitable(args_list):
                args_list = await args_list
            if not isinstance(args_list, list):
                args_list = [args_list]
            for prepared_args in args_list:
                #Step 2: Invoke
                future = asyncio.Future()
                completion_futures.append(future)
                invokation_task = asyncio.create_task(self.invoke(prepared_args))
                # Step 3: Handle Response
                invokation_task.add_done_callback(lambda t, future=future: self.__get_output__(t.result(), future=future, chain=chain))
            return await asyncio.gather(*completion_futures)
        task = asyncio.create_task(run_with())
        task.add_done_callback(lambda _: chain.mark_completed())
        return chain
    return fn