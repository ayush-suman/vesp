from abc import ABC, abstractmethod
import inspect
from typing import get_origin, get_type_hints

from vespwood._utils.json_schema import type_to_json_schema


class Schematic(ABC):
    """
    A class that is the base class of Schema, Tool or Agent.
    Schematic has name, description and schema properties.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str | None:
        ...

    @property
    @abstractmethod
    def schema(self) -> dict[str, any]:
        """
        Get the parameters of the function as a JSON schema.

        :return: A dictionary representing the JSON schema of the function parameters.
        """
        ...