from abc import abstractmethod
import asyncio
import inspect
from typing import Any, Awaitable, ParamSpec, TypeVar, Protocol, cast
from urllib.parse import urlparse
from vesp.invokation import InvokationRestoreData, OutputFuture, Invokation
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



CP = ParamSpec("CP")
CO = TypeVar("CO")
class CallableAgent(Protocol[CP, CO]):
    def __call__(self, *args: CP.args, **kwds: CP.kwargs) -> CO:
        ...


I = ParamSpec("I")
O = TypeVar("O")
C = TypeVar("C")
        
class Agent(BaseAgent[I, O]):
    @abstractmethod
    def prepare_args(self, *args: I.args, **kwargs: I.kwargs): 
        ...

    @abstractmethod
    def __invoke__(self: CallableAgent[CP, CO], prepared_args: dict[str, Any], *args: CP.args, **kwargs: CP.kwargs) -> Run[dict[str, Any]]:
        '''Accepts args, and returns outputs for the Invokation chain object'''
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

    async def on_responses(self, args: dict[str, Any], extras: dict[str, Any]) -> None:
        ...

    def handle_responses(self, **kwargs) -> O:
        return kwargs

    async def on_complete(self, output: O) -> None:
        ...

    def __call__(self: AgentLike[P, O_co], *args: P.args, **kwds: P.kwargs) -> Invokation[O_co]:
        agent = cast("Agent[P, O_co]", self)
        invokation = Invokation()

        def __post_run_setup__(run: Run[dict[str, Any]]) -> OutputFuture[O]:
            def on_invoke(output_args: dict[str, Any]) -> asyncio.Task[O]:
                handle_responses = suppliment(agent.handle_responses, **output_args)
                handle_responses_task = asyncio.create_task(handle_responses())
                return handle_responses_task
            class AgentOutputFuture(OutputFuture[O]):
                def post_run_processing(future, run_result: dict[str, Any]) -> Awaitable[O]:
                    return on_invoke(run_result)
            return AgentOutputFuture(run)

        def invoke(prepared_args: dict[str, Any]) -> OutputFuture[O]:
            run = agent.__invoke__(prepared_args, *args, **kwds)
            run.add_on_pause_callback(agent.on_pause)
            run.add_on_resume_callback(agent.on_resume)
            run.add_on_error_callback(agent.on_error)
            run.add_on_cancel_callback(agent.on_cancel)
            output_future = __post_run_setup__(run)
            future = invokation.promise_output(output_future)
            return future
        
        if inspect.isgeneratorfunction(self.prepare_args): 
            generator = self.prepare_args(*args, **kwds)
            prepared_args = next(generator)
            try:
                while True:
                    future_output = invoke(prepared_args)
                    prepared_args = generator.send(future_output._run)
            except StopIteration:
                invokation.promise_complete()

        elif inspect.isasyncgenfunction(self.prepare_args): 
            generator = self.prepare_args(*args, **kwds)
            next_task = asyncio.create_task(anext(generator))
            try:
                while True:
                    awaitable = None
                    def on_task_done(t: asyncio.Task):
                        nonlocal awaitable
                        awaitable = invoke(t.result())
                    next_task.add_done_callback(on_task_done)
                    next_task = asyncio.create_task(generator.asend(awaitable))
            except StopIteration:
                invokation.promise_complete()

        elif inspect.iscoroutinefunction(self.prepare_args):
            prepare_args_task = asyncio.create_task(self.prepare_args(*args, **kwds))
            def on_prepare_args_done(prepared_args_t: asyncio.Task[dict[str, Any]]):
                prepared_args = prepared_args_t.result()
                if isinstance(prepared_args, dict): 
                    invoke(prepared_args)
                else:
                    for a in prepared_args: 
                        invoke(a)
                invokation.promise_complete()
            prepare_args_task.add_done_callback(on_prepare_args_done)

        else:
            prepared_args = self.prepare_args(*args, **kwds)
            if isinstance(prepared_args, dict): 
                invokation.promise_output()
                invoke(prepared_args)
            else:
                for a in prepared_args: 
                    invokation.promise_output()
                    invoke(a)
            invokation.promise_complete()


    def resume_with(self, restore_data: list[InvokationRestoreData]) -> Invokation[O]:
        # TODO: full call rewritten from valid checkpoint
        ...

    
