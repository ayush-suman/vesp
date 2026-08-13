import asyncio
import inspect
from typing import Any, ParamSpec, TypeVar, Callable, Concatenate, Generator, AsyncGenerator

from vesp.invokation import Invokation
from .agent import Agent


I = ParamSpec("I")
O = TypeVar("O")

def yields_args(func: Callable[Concatenate[Agent[I, O], I], Generator[dict[str, Any], asyncio.Future, None]] | AsyncGenerator[dict[str, Any], asyncio.Task] | None = None) -> Callable[Concatenate[Agent[I, O], I], Invokation[O]]:
    def fn(self: Agent[I, O], *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        chain = Invokation()
        async def run():
            completion_futures: list[asyncio.Future] = []

            def run_with(prepared_args) -> asyncio.Future:
                #Step 2: Invoke
                future = asyncio.Future()
                completion_futures.append(future)
                invokation_task = asyncio.create_task(self.invoke(prepared_args))
                # Step 3: Handle Response
                invokation_task.add_done_callback(lambda t, future=future: self.__get_output__(t.result(), future=future, chain=chain))
                return future
            
            if inspect.isgeneratorfunction(func):
                generator: Generator[dict[str, Any], asyncio.Task, None] = func(self, *args, **kwargs)
                try:
                    yielded_args = next(generator)
                    while True:
                        future = run_with(yielded_args)
                        yielded_args = generator.send(future)
                        
                except StopIteration:
                    pass

            elif inspect.isasyncgenfunction(func):
                generator: AsyncGenerator[dict[str, Any], asyncio.Task] = func(self, *args, **kwargs)
                try:
                    yielded_args = await anext(generator)
                    while True:
                        future = run_with(yielded_args)
                        yielded_args = await generator.asend(future)
                        
                except StopAsyncIteration:
                    pass

            return await asyncio.gather(*completion_futures)

        task = asyncio.create_task(run())
        task.add_done_callback(lambda _: chain.mark_completed())
        return chain
    return fn