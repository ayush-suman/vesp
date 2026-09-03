from __future__ import annotations
import json
from typing import Any


class Structured(dict[str, Any]):
    def __init__(self, data: str | dict):
        if isinstance(data, str): super().__init__(json.loads(data))
        else: super().__init__(data)


    def __getitem__(self, key: str):
        def getvalue(obj, key):
            if isinstance(obj, dict): 
                return dict.get(obj, key)
            elif isinstance(obj, list): 
                return [getvalue(item, key) for item in obj]
            else: return None
        if key == "." or key == "":
            return dict(self)
        if key.startswith("."):
            key = key[1:]
        while "." in key and self is not None:
            base, key = key.split('.', 1)
            self = getvalue(self, base)
        return getvalue(self, key) if self else None
    
    
    def get(self, key: str, default: Any = None):
        return self.__getitem__(key) or default

    def copy(self) -> Structured:
        return Structured(dict(self))