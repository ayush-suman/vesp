from abc import ABC, abstractmethod
from typing import Any
from vespwood.prompt_structure.prompt_structure import PromptStructure


class Executor(ABC):
    @abstractmethod
    async def execute(self,  name: str, description: str | None, prompt_structure: PromptStructure, args: dict[str, Any]) -> dict[str, Any]:
        ...
    