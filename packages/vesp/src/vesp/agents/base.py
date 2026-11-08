from __future__ import annotations
from abc import abstractmethod
from copy import copy
from typing import Any, Callable, ParamSpec, TypeVar, Generic

from vesp.invokation import Invokation, OutputFuture
from vespwood.run import Run


I = ParamSpec("I")
O = TypeVar("O")
C = TypeVar("C")
class BaseAgent(Generic[I, O]):
    class AgentsGroup("BaseAgent"):
        def __init__(self, agents: list[BaseAgent]):
            self._agents = agents

        def __call__(self, *args, **kwargs) -> Invokation:
            invokation = Invokation(args, kwargs)
            tbd_count = 0
            for agent in self._agents:
                tbd_count += 1
                def dec_tbd_count():
                    tbd_count -= 1
                    if tbd_count == 0: invokation.promise_complete()
                i = agent(args, kwargs)
                i.add_on_output_promise_callback(invokation.promise_output)
                i.add_on_complete_promise_callback(dec_tbd_count)
            return invokation
            

    @abstractmethod
    def __call__(self, *args: I.args, **kwds: I.kwargs) -> Invokation[O]:
        ...

    def __getitem__(self, morph: Callable[[C], list[tuple[Any] | dict[str, Any]]]) -> "BaseAgent":
        cls = type(self)
        class MorphInputMixin:
            def __call__(agent, input: C) -> Invokation[O]:
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
    

    def __pow__(self, other: BaseAgent | BaseAgent.AgentsGroup) -> "BaseAgent":
        cls = type(self)
        class PowChainMixin:
            def __call__(agent: BaseAgent, *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
                invokation: Invokation[O] = super().__init__(args, kwargs)
                def on_output_promise(of: OutputFuture[O]):
                    def on_output(output: O):
                        next = other(output)
                        if isinstance(next, Invokation):
                            of.add_next(next)
                        elif isinstance(next, list):
                            [of.add_next(each) for each in next]
                    of.add_on_output_callback(on_output)
                invokation.add_on_output_promise_callback(on_output_promise)
                return invokation

        new = type(f"{cls.__name__}Pow{other.__class__.__name__}", (PowChainMixin, cls), {})
        new_self = copy(self)
        new_self.__class__ = new
        return new_self


    def __or__(self, other: BaseAgent | BaseAgent.AgentsGroup):
        cls = type(self)
        class OrChainMixin:
            def __call__(agent: BaseAgent, *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
                invokation: Invokation[O] = super().__call__(args, kwargs)
                def on_complete(inv: Invokation[O], *a, **k):
                    next = other(*a, **k)
                    if isinstance(next, Invokation):
                        inv.add_next(next)
                    elif isinstance(next, list): 
                        [inv.add_next(each) for each in next]
                invokation.add_on_complete_callback(lambda a=args, k=kwargs, inv=invokation: on_complete(inv, *a, **k))
                return invokation

        new = type(f"{cls.__name__}Or{other.__class__.__name__}", (OrChainMixin, cls), {})
        new_self = copy(self)
        new_self.__class__ = new
        return new_self

    def __add__(self, other: BaseAgent | BaseAgent.AgentsGroup) -> BaseAgent.AgentsGroup:
        if isinstance(other, BaseAgent.AgentsGroup): return other + self
        if other.__class__.__name__ == self.__class__.__name__:
            raise ValueError("Can not add agents of same class names")
        return BaseAgent.AgentsGroup([self, other])
