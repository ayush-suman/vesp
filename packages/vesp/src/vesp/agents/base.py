from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Literal, ParamSpec, TypeVar, Generic
from vespwood import Tool

from vesp.invokation import Invokation


class AgentMeta(ABCMeta):
    def __sub__(cls, other: Literal["public", "private"]) -> AgentMeta:
        class ScopedAgent(cls):
            def __init__(self):
                self._accessibility = other

        ScopedAgent.__class__.__name__ = cls.__name__
        ScopedAgent.__class__.__qualname__ = cls.__qualname__
        return ScopedAgent


I = ParamSpec("I")
O = TypeVar("O")
class BaseAgent(Generic[I, O], metaclass=AgentMeta): 
    def __init__(self):
        self._accessibility = "private"

    def __sub__(self, other: Literal["public", "private"]) -> "BaseAgent":
        self._accessibility = other
        return self

    @property
    def is_public(self):
        return self._accessibility == "public"

    @abstractmethod
    def __call__(self, *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        pass