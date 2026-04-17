from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Literal
from vespwood import Schematic

from vesp.invokation import Invokation


class AgentMeta(ABCMeta):
    def __sub__(cls, other: Literal["public", "private"]) -> AgentMeta:
        class ScopedAgent(cls):
            def __init__(self):
                self._accessibility = other

        ScopedAgent.__class__.__name__ = cls.__name__
        ScopedAgent.__class__.__qualname__ = cls.__qualname__
        return ScopedAgent


class BaseAgent(Schematic, metaclass=AgentMeta): 
    def __init__(self):
        self._accessibility = "private"

    def __sub__(self, other: Literal["public", "private"]) -> "BaseAgent":
        self._accessibility = other
        return self

    @property
    def is_public(self):
        return self._accessibility == "public"

    @abstractmethod
    def __call__(self, *args, **kwargs) -> Invokation:
        pass