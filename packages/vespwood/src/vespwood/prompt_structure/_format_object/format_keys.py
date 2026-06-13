from __future__ import annotations
from typing import Any

from vespwood._utils.get_base_index import get_key_index
from vespwood.prompt_mapping import PromptMapping
from vespwood.types.params import Params

from .format_object import FormatObject
from .format_list import FormatList


# TODO: use to_format_object everywhere instead of directly using FormatKeys
class FormatKeys(dict[str, FormatObject | None], FormatObject):
    def __init__(self, value: dict[str, FormatObject | None] = {}, *, extras: dict[str, Any] = {}):
        for k, v in value.items():
            if v is not None and not isinstance(v, FormatObject):
                raise ValueError("All values must be instances of FormatObject")
            self.__setitem__(k, v)
        self.__extras__ = extras


    def update(self, value: dict[str, FormatObject | None], *, extras: dict[str, Any] = {}):
        if not all(isinstance(v, FormatObject) for v in value.values() if v is not None):
            raise ValueError("All values must be instances of FormatObject")
        for k, v in value.items():
            if v is not None and not isinstance(v, FormatObject):
                raise ValueError("All values must be instances of FormatObject")
            self.__setitem__(k, v)
        self.__extras__ = extras


    def copy_with(self, extra_keys: dict[str, FormatObject | None]) -> "FormatKeys":
        if not all(isinstance(v, FormatObject) for v in extra_keys.values() if v is not None):
            raise ValueError("All extra keys must be instances of FormatObject")
        return FormatKeys({**self, **extra_keys}, extras=self.extras)
    
    
    @property
    def is_class_object(self) -> bool:
        """Uses __object__'s class as a signature to verify by matching with __class__"""
        return "__class__" in self.extras and "__object__" in self.extras and getattr(self.extras["__object__"], "__class__", None) == self.extras["__class__"]


    def __getattr__(self, name):
        return self.__getitem__(name)
    

    def __hasattr__(self, name):
        return self.__contains__(name)
    

    def __getitem__(self, key: str):
        if key.startswith("_"):
            return None
        
        if "?" in key:
            base_key, extra_key = key.split("?", 1)
            object = self if base_key == "" else self.__getitem__(base_key)
            if object is None: return None
            return FormatObject.__getitem__(object, extra_key)

        # if "." in key:
        #     parts = key.split(".")
        #     value = self
        #     for part in parts:
        #         if hasattr(value, part):
        #             value = getattr(value, part)
        #         else:
        #             return None
        #     return value
        
        if "#" in key:
            key, index = get_key_index(key)
            base = self.__getitem__(key)
            if base:
                if index >= len(base):
                    return None
                return base.__getitem__(index)
            
        if key in self: 
            return dict.__getitem__(self, key)

        return None
    

    def __setitem__(self, key: str, value):
        if "?" in key:
            base_key, extra_key = key.split("?", 1)
            object = self if base_key == "" else self.__getitem__(base_key)
            if object is None:
                raise ValueError(f"To set {value} to {extra_key} at {base_key}, there should be some value present at {base_key}")
            return FormatObject.__setitem__(object, extra_key, value)
        
        if value is not None and not isinstance(value, FormatObject):
            raise ValueError("Only instances of FormatObject can be assigned to FormatKeys")
        
        # if "." in key:
        #     rest, last = key.rsplit(".", 1)
        #     if self.__getitem__(rest):
        #         base = self.__getitem__(rest)
        #         base.__setitem__(last, value)
        #     else:
        #         self.__setitem__(rest, FormatKeys({last: value}))
        #     return

        if "#" in key:
            key, index = get_key_index(key)
            base = self.__getitem__(key)
            if base:
                assert isinstance(base, FormatList)
                if index >= len(base): 
                    base.extend([None] * (index - len(base) + 1))
                base.__setitem__(index, value)
            else:
                self.__setitem__(key, FormatList([*[None] * (index - 1), value]))
            return

        if self.is_class_object:
            setattr(
                self.extras["__object__"], 
                key, 
                value.normalized if value is not None else None
            )

        dict.__setitem__(self, key, value)


    def get_params(self, keys: Params) -> PromptMapping:
        params = PromptMapping({})
        for k in keys:
            if isinstance(k, str): params[k] = self[k]
            else:
                key, alias = next(iter(k.items()))
                params[alias] = self[key]
        return params
    

    @property
    def normalized(self) -> dict[str, Any]:
        if self.is_class_object:
            return self.extras["__object__"]
        return { k: v.normalized if v is not None else None for k, v in self.items() }
    
    @property
    def json(self) -> dict[str, Any]:
        return { k: v.json if v is not None else None for k, v in self.items() }
    
    
    def __repr__(self) -> str:
        return repr({k: v for k, v in self.items() if not k.startswith("_")})
    

    def __str__(self) -> str:
        return str({k: v for k, v in self.items() if not k.startswith("_")})
    