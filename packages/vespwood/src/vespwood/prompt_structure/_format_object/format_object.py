from typing import Any
from abc import ABC, abstractmethod


class FormatObject(ABC):
    __extras__: dict[str, Any] = {}


    @property
    def extras(self) -> dict[str, Any]:
        return getattr(self, "__extras__", {})
    

    @property
    @abstractmethod
    def normalized(self) -> Any:
        ...

    @property
    @abstractmethod
    def json(self) -> Any:
        ...