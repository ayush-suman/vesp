from __future__ import annotations
from abc import abstractmethod
from copy import copy
from typing import Any, Callable, ParamSpec, TypeVar, Generic
from vesp.invokation import Invokation, OutputFuture


I = ParamSpec("I")
O = TypeVar("O")
C = TypeVar("C")
class BaseAgent(Generic[I, O]):
    @abstractmethod
    def __call__(self, *args: I.args, **kwds: I.kwargs) -> Invokation[O]:
        ...

    def __getitem__(self, morph: Callable[[C], list[tuple[Any] | dict[str, Any]]]) -> "BaseAgent":
        class MorphedInputAgent(BaseAgent):
            def __call__(agent, input: C) -> Invokation[O]:
                def _(res):
                    if isinstance(res, dict): return ((), res)
                    elif isinstance(res, tuple): return (res, {})
                    else: raise ValueError(f"{res} is neither tuple nor dict")
                args, kwargs = _(morph(input))
                return super().__call__(*args, **kwargs)
        return MorphedInputAgent()

    def __pow__(self, other: BaseAgent) -> BaseAgent:
        class PowAgentGroup(BaseAgent):
            def __call__(agent: BaseAgent, *args: I.args, **kwargs: I.kwargs) -> Invokation:
                invokation = Invokation(args, kwargs)
                count = 0
                inv = self(*args, **kwargs)
                def on_output_promise():
                    nonlocal count
                    count += 1
                def on_complete_promise():
                    nonlocal count
                    count -= 1
                    if count == 0:
                        invokation.promise_complete()
                def on_output(o):
                    i = other(o)
                    i.add_on_output_promise_callback(invokation.promise_output)
                    i.add_on_complete_promise_callback(on_complete_promise)
                inv.add_on_output_promise_callback(on_output_promise)
                inv.add_on_output_callback(on_output)
                return invokation
        return PowAgentGroup()

    def __or__(self, other: BaseAgent):
        class OrAgentGroup(BaseAgent):
            def __call__(agent: BaseAgent, *args: I.args, **kwargs: I.kwargs) -> Invokation:
                invokation = Invokation(args, kwargs)
                inv = self(*args, **kwargs)
                def on_complete(_):
                    i = other(*args, **kwargs)
                    i.add_on_output_promise_callback(invokation.promise_output)
                    i.add_on_complete_promise_callback(lambda _: invokation.promise_complete)
                inv.add_on_complete_callback(on_complete)
                return invokation
        return OrAgentGroup()

    def __add__(self, other: BaseAgent) -> BaseAgent:
        class AddAgentGroup(BaseAgent):
            def __call__(self, *args, **kwargs) -> Invokation:
                invokation = Invokation(args, kwargs)
                tbd_count = 0
                for agent in (self, other):
                    tbd_count += 1
                    def dec_tbd_count():
                        nonlocal tbd_count
                        tbd_count -= 1
                        if tbd_count == 0: invokation.promise_complete()
                    i = agent(args, kwargs)
                    i.add_on_output_promise_callback(invokation.promise_output)
                    i.add_on_complete_promise_callback(dec_tbd_count)
                return invokation
        return AddAgentGroup()



