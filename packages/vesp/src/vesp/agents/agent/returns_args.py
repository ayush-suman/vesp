import asyncio
import inspect
from typing import ParamSpec, TypeVar, Callable, Concatenate, Iterator

from vesp.invokation import Invokation
from vespwood import (
    PreparedArgs
)

from .agent import Agent


I = ParamSpec("I")
O = TypeVar("O")

def returns_args(func: Callable[Concatenate[Agent[O], I], Iterator[PreparedArgs]] | None = None)  -> Callable[Concatenate[Agent[O], I], Invokation[O]]:
    def fn(self: Agent[O], *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        chain = Invokation()
        async def run_with():
            completion_futures: list[asyncio.Future] = []
            # Step 1: Prepare Args
            prepared_args_list = await func(self, *args, **kwargs)
            for prepared_args in prepared_args_list:
                #Step 2: Invoke
                future = asyncio.Future()
                completion_futures.append(future)
                invokation_task = asyncio.create_task(self.invoke(prepared_args))
                # Step 3: Handle Response
                invokation_task.add_done_callback(lambda t, future=future: self.__get_output__(*t.result(), future=future, chain=chain))
            return await asyncio.gather(*completion_futures)
        task = asyncio.create_task(run_with())
        task.add_done_callback(lambda _: chain.mark_completed())
        return chain
    fn.__signature__ = inspect.signature(func)
    return fn