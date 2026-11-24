from __future__ import annotations
from abc import abstractmethod
import asyncio
import inspect
from typing import Any, Awaitable, Callable, Concatenate, ParamSpec, TypeVar, Protocol, cast
from vesp.invokation import InvokationRestoreData, Invokation
from vespwood.run import Run
from vespwood_generator import suppliment

from vesp.agents import BaseAgent


P = ParamSpec("P")
O_co = TypeVar("O_co", covariant=True)
class AgentLike(Protocol[P, O_co]):
    def prepare_args(self, *args: P.args, **kwargs: P.kwargs) -> Any:
        ...

    def handle_responses(self, **kwargs: Any) -> O_co | Awaitable[O_co]: 
        ...



I = ParamSpec("I")
O = TypeVar("O")
C = TypeVar("C")
        
class Agent(BaseAgent[Concatenate[Callable[[dict[str, Any]], Run], I], O]):
    @abstractmethod
    def prepare_args(self, *args: I.args, **kwargs: I.kwargs): 
        ...

    async def on_start(self, args: dict[str, Any]) -> None:
        ...

    async def on_pause(self, args: dict[str, Any], extras: dict[str, Any]) -> None:
        ...

    async def on_resume(self, args: dict[str, Any], extras: dict[str, Any]) -> None:
        ...

    async def on_error(self, exception: Exception, args: dict[str, Any], extras: dict[str, Any]) -> None:
        ...

    async def on_cancel(self, args: dict[str, Any], extras: dict[str, Any]) -> None:
        ...

    async def on_retry(self, args: dict[str, Any], extras: dict[str, Any]) -> None:
        ...

    def handle_responses(self, **kwargs) -> O:
        return kwargs

    async def on_complete(self, output: O) -> None:
        ...

    def __call__(self: AgentLike[P, O_co], invokable: Callable[[dict[str, Any]], Run], *args: P.args, **kwargs: P.kwargs) -> Invokation[O_co]:
        agent = cast(Agent[P, O_co], self)

        def on_invoke(output_args: dict[str, Any]) -> Awaitable[O]:
            handle_responses = suppliment(agent.handle_responses, **output_args)
            return handle_responses()

        invokation = Invokation(args, kwargs, on_invoke)

        def on_args(prepared_args: dict[str, Any]):
            run = invokable(prepared_args)
            run.add_on_pause_callback(agent.on_pause)
            run.add_on_resume_callback(agent.on_resume)
            run.add_on_error_callback(agent.on_error)
            run.add_on_cancel_callback(agent.on_cancel)
            run.add_on_retry_callback(agent.on_retry)
            invokation.add_on_output_callback(agent.on_complete)
            invokation.promise_output(run)
        
        if inspect.isgeneratorfunction(self.prepare_args): 
            generator = self.prepare_args(*args, **kwargs)
            for args in generator:
                on_args(args)
            invokation.promise_complete()

        elif inspect.isasyncgenfunction(self.prepare_args): 
            generator = self.prepare_args(*args, **kwargs)
            async def drive():
                async for args in generator:
                    on_args(args)
                invokation.promise_complete()
            asyncio.create_task(drive())

        elif inspect.iscoroutinefunction(self.prepare_args):
            prepare_args_task = asyncio.create_task(self.prepare_args(*args, **kwargs))
            def on_prepare_args_done(prepared_args_t: asyncio.Task[dict[str, Any]]):
                prepared_args = prepared_args_t.result()
                if isinstance(prepared_args, dict): 
                    on_args(prepared_args)
                else:
                    for a in prepared_args: 
                        on_args(a)
                invokation.promise_complete()
            prepare_args_task.add_done_callback(on_prepare_args_done)

        else:
            prepared_args = self.prepare_args(*args, **kwargs)
            if isinstance(prepared_args, dict): 
                on_args(prepared_args)
            else:
                for a in prepared_args: 
                    on_args(a)
            invokation.promise_complete()
        
        return invokation
        

    def resume_with(self, restore_data: list[InvokationRestoreData]) -> Invokation[O]:
        # TODO: full call rewritten from valid checkpoint
        ...

    