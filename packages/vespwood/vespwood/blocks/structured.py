import json
from typing import Any


class Structured(dict[str, Any]):
    def __init__(self, data: str | dict):
        if isinstance(data, str):
            super().__init__(json.loads(data))
        else:
            super().__init__(data)

    def __getitem__(self, key):
        if "." in key:
            key_parts = key.split('.')
            value = self
            for part in key_parts:
                if part in value:
                    value = value.__getitem__(part)
            return value
        if key in self:
            return super().__getitem__(key)
        return None
    
    def get(self, key: str, default: Any = None):
        value = self[key]
        if value is None:
            return default
        return value
