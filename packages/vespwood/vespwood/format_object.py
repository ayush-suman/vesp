from typing import Any
from vespwood.prompt_mapping import PromptMapping
from vespwood.types.params import Params
from vespwood._utils import get_key_index


def deep_convert(data: Any) -> Any:
    if isinstance(data, dict) and not isinstance(data, FormatKeys):
        return FormatKeys({k: deep_convert(v) for k, v in data.items()})
    if isinstance(data, list) and not isinstance(data, FormatList):
        return FormatList(data)
    skip_types = (int, float, bool, str, bytes, FormatKeys, FormatList)
    if not isinstance(data, skip_types):
        cls = data.__class__
        annotations = getattr(cls, "__annotations__", {})
        return FormatKeys({name: deep_convert(getattr(data, name)) for name in annotations})
    return data


class FormatObject:
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
    

class FormatList(list, FormatObject):
    def __init__(self, value: list):
        super().__init__([deep_convert(v) for v in value])

    def append(self, v: Any) -> None:
        super().append(deep_convert(v))

    def extend(self, it) -> None:
        super().extend(deep_convert(v) for v in it)

    def insert(self, i: int, v: Any) -> None:
        super().insert(i, deep_convert(v))

    def __setitem__(self, i, v) -> None:
        if isinstance(i, slice):
            super().__setitem__(i, [deep_convert(x) for x in v])
        else:
            super().__setitem__(i, deep_convert(v))

    
class FormatKeys(dict[str, Any], FormatObject):
    def __init__(self, value: dict[str, Any] = {}):
        for k, v in value.items():
            super().__setitem__(k, deep_convert(v))

    @classmethod
    def from_format_keys(cls, format_keys: "FormatKeys", **new_keys):
        return cls({ **format_keys, **new_keys })

    def copy_with_extra(self, **extra_keys):
        return FormatKeys.from_format_keys(self, **extra_keys)


    def __getattr__(self, name):
        return self.__getitem__(name)
    
    def __hasattr__(self, name):
        return self.__contains__(name)
    

    def __getitem__(self, key: str):
        if "." in key:
            parts = key.split(".")
            value = self
            for part in parts:
                if hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            return value
        
        if "#" in key:
            key, index = get_key_index(key)
            base = self.__getitem__(key)
            if base:
                if index >= len(base):
                    return None
                return base.__getitem__(index)
        if key in self: 
            return super().__getitem__(key)
    

    def __setitem__(self, key, value):
        value = deep_convert(value)
        if "#" in key:
            key, index = get_key_index(key)
            base = self.__getitem__(key)
            if base:
                assert isinstance(base, list)
                if index >= len(base): 
                    base.extend([None] * (index - len(base) + 1))
                base.__setitem__(index, value)
            else:
                self.__setitem__(key, [*[None] * (index - 1), value])
        else:
            super().__setitem__(key, value)
    

    def update(self, value: dict[str, Any]):
        value = deep_convert(value)
        super().update(value)


    def get_params(self, keys: Params) -> PromptMapping:
        params = PromptMapping({})
        print(self.keys())
        for k in keys:
            if isinstance(k, str): params[k] = self[k]
            else:
                key, alias = next(iter(k.items()))
                params[alias] = self[key]
        return params
    