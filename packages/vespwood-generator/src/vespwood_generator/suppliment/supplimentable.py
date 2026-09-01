from __future__ import annotations
import inspect
from typing import Any, Callable, get_type_hints

from vespwood_generator._utils import Param, filter_params
from .suppliment import suppliment
from .supplimented import Supplimented


class Supplimentable:
    __skip_params__: list[str]
    __params__: dict[str, inspect.Parameter]
    __type_hints__: dict[str, Any]

    def __class_getitem__(cls, skip_params: str | tuple[str, ...]) -> type[Supplimentable]:
        params = []
        print("skip_params", skip_params)
        if isinstance(skip_params, tuple):
            params = list(skip_params)
        else:
            params = [skip_params]
        return type(cls.__name__, (cls,), {"__skip_params__": params})

    def infer_params_from(self, fn: Callable):
        sig = inspect.signature(fn)
        self.__params__ = sig.parameters
        self.__type_hints__ = get_type_hints(fn)

    def add_param(self, name: str, type: type, optional: bool = False):
        if not hasattr(self, "__params__"):
            self.__params__ = {}
        if not hasattr(self, "__type_hints__"):
            self.__type_hints__ = {}
        self.__params__[name] = inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None if optional else inspect.Parameter.empty)
        self.__type_hints__[name] = type

    @property
    def params_inferred(self) -> bool:
        return hasattr(self, "__parameters__") and hasattr(self, "__type_hints__")
    
    def suppliment(self, **kwargs) -> Supplimented:
        supplimented_args: dict[str, Any] = {}
        params = filter_params(self.__params__, self.__type_hints__, self.__skip_params__, **kwargs)
        for param in params:
            if param.optional:
                if param.name in kwargs:
                    supplimented_args[param.name] = kwargs[param.name]
            else:
                if param.name not in kwargs:
                    raise KeyError(param.name)
                supplimented_args[param.name] = kwargs[param.name]
        return Supplimented(self, **supplimented_args)
    