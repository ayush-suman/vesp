from abc import ABC, abstractmethod
from typing import Any, Self

class Matchable(ABC):
    @abstractmethod
    def format_map(self, mapping: dict[str, Any]) -> Self:
        ...

    
    @abstractmethod
    def match(self, val: Any) -> bool:
        ...