from typing import Any
from abc import ABC, abstractmethod


class FormatObject(ABC):
    __extras__: dict[str, Any] = {}


    @property
    def extras(self) -> dict[str, Any]:
        return getattr(self, "__extras__", {})


    def __format__(self, format_spec: str):
        value = self
        match format_spec:
            case "pretty":
                import json
                value = json.dumps(value, indent=2)
            case "count" | "length":
                return str(len(value))
            case _:
                value = format(str(value), format_spec)
        return value
    

    @property
    @abstractmethod
    def normalized(self) -> Any:
        ...

    def __getitem__(self, key: str):
        return self.extras.get(key)

    def __setitem__(self, key: str, value: Any):
        self.extras[key] = value