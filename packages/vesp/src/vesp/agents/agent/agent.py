from abc import abstractmethod
import asyncio
from copy import copy
import inspect
from pathlib import Path
from types import MethodType
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar, Protocol, cast, Generic
from urllib.parse import urlparse
from vesp.invokation import InvokationRestoreData, OutputFuture, Invokation
from vespwood.run import Run
from vespwood_generator import suppliment
from vesp.errors import InvalidStateError

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
    class AgentsList(list["Agent"]):
        # TODO: Implement modified resume_with
        def __init__(self, runners: list[Agent], *, next: Agent | list[Agent] | None = None, await_all: bool = False):
            self._next = next
            self._await_all = await_all
            super().__init__(runners)

        def __pow__(self, other: Agent | list[Agent]):
            base = type(self)
            class RunnerWithNoAwaitNext(base): ...
            RunnerWithNoAwaitNext.__name__ = base.__name__
            RunnerWithNoAwaitNext.__qualname__ = base.__qualname__
            RunnerWithNoAwaitNext.__module__ = base.__module__
            return RunnerWithNoAwaitNext(self, next=other, await_all=False)

        def __or__(self, other: Agent | list[Agent]):
            base = type(self)
            class RunnerWithAwaitNext(base): ...
            RunnerWithAwaitNext.__name__ = base.__name__
            RunnerWithAwaitNext.__qualname__ = base.__qualname__
            RunnerWithAwaitNext.__module__ = base.__module__
            return RunnerWithAwaitNext(self, next=other, await_all=True)

        def __add__(self, other: Agent)  -> "Agent.AgentsList":
            if other.__class__.__name__ in [agent.__class__.__name__ for agent in self]:
                raise ValueError(f"Can not add agents of same class names")
            return Agent.AgentsList([*self , other])

        def __call__(self, *args, **kwargs) -> list[Invokation]:
            return [agent(*args, **kwargs) for agent in self]


    @abstractmethod
    def prepare_args(self, *args: I.args, **kwargs: I.kwargs): 
        ...

    @abstractmethod
    def invoke(self: CallableAgent[CP, CO], prepared_args: dict[str, Any], *args: CP.args, **kwargs: CP.kwargs) -> Run[dict[str, Any]]:
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


    def __str__(self):
        return self._name


    def __repr__(self):
        return self._name


    def __on_invoke__(self, run: Run[dict[str, Any]]) -> OutputFuture[O]:
        def on_invoke(output_args: dict[str, Any]) -> asyncio.Task[O]:
            handle_responses = suppliment(self.handle_responses, **output_args)
            handle_responses_task = asyncio.create_task(handle_responses())
            return handle_responses_task
        class AgentOutputFuture(OutputFuture[O]):
            def set_post_run_callback(future, run_result: dict[str, Any]) -> Awaitable[O]:
                return on_invoke(run_result)
        return AgentOutputFuture(run)


    def __call__(self: AgentLike[P, O_co], *args: P.args, **kwds: P.kwargs) -> Invokation[O_co]:
        agent = cast("Agent[P, O_co]", self)
        invokation = Invokation()

        def invoke(prepared_args: dict[str, Any]) -> OutputFuture[O]:
            run = agent.invoke(prepared_args, *args, **kwds)
            run.add_on_pause_callback(agent.on_pause)
            run.add_on_resume_callback(agent.on_resume)
            run.add_on_error_callback(agent.on_error)
            run.add_on_cancel_callback(agent.on_cancel)
            output_future = agent.__on_invoke__(run)
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

    def __getitem__(self, morph: Callable[[C], list[tuple[Any] | dict[str, Any]]]) -> "Agent":
        cls = type(self)
        class MorphInputMixin:
            def __call__(agent: AgentLike, input: C) -> Invokation[O_co]:
                def _(res):
                    if isinstance(res, dict): return ((), res)
                    elif isinstance(res, tuple): return (res, {})
                    else: raise ValueError(f"{res} is neither tuple nor dict")
                args, kwargs = _(morph(input))
                return super().__call__(*args, **kwargs)
        new = type(cls.__name__, (MorphInputMixin, cls), {})
        new_self = copy(self)
        new_self.__class__ = new
        return new_self
    

    def __pow__(self, other: Agent | Agent.AgentsList) -> Agent:
        cls = type(self)
        class PowChainMixin:
            # TODO: Implement modified resume_with
            def __on_invoke__(agent, run: Run[dict[str, Any]]) -> OutputFuture[O]:
                output_future: OutputFuture[O] = super().__on_invoke__(run)
                def on_output(future: OutputFuture, output: O_co):
                    next = other(output)
                    if isinstance(next, Invokation):
                        future.add_next(next)
                    elif isinstance(next, list): 
                        [future.add_next(each) for each in next]
                output_future.add_on_output_callback(lambda output, future=output_future: on_output(future, output))
                return output_future

        new = type(f"{cls.__name__}Pow{other.__class__.__name__}", (PowChainMixin, cls), {})
        new_self = copy(self)
        new_self.__class__ = new
        return new_self


    def __or__(self, other: Agent | Agent.AgentsList):
        cls = type(self)
        class OrChainMixin:
            # TODO: Implement modified resume_with
            def __call__(agent: AgentLike, *args: P.args, **kwargs: P.kwargs) -> Invokation[O_co]:
                invokation: Invokation[O_co] = super().__call__(args, kwargs)
                def on_complete(inv: Invokation[O_co], *a, **k):
                    next = other(*a, **k)
                    if isinstance(next, Invokation):
                        inv.add_next(next)
                    elif isinstance(next, list): 
                        [inv.add_next(each) for each in next]
                invokation.add_on_complete_callback(lambda a=args, k=kwargs, inv=invokation: on_complete(inv, *a, **k))

        new = type(f"{cls.__name__}Or{other.__class__.__name__}", (OrChainMixin, cls), {})
        new_self = copy(self)
        new_self.__class__ = new
        return new_self


    def __add__(self, other: Agent | Agent.AgentsList) -> Agent.AgentsList:
        if isinstance(other, Agent.AgentsList): return other + self
        if other.__class__.__name__ == self.__class__.__name__:
            raise ValueError("Can not add agents of same class names")
        return Agent.AgentsList([self, other])

