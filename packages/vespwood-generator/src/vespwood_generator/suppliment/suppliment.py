import types
from typing import Any, Callable, ParamSpec, TypeVar

from vespwood_generator._utils import filter_params
from vespwood_generator.suppliment.supplimented import Supplimented


I = ParamSpec("I")
O = TypeVar("O")
def suppliment(callable_obj: Callable[I, O], skip_params: list[str] = [], /, **args: dict[str, Any]) -> Supplimented[O]:
    params = filter_params(callable_obj, skip_params, **args)
    supplimented_args: dict[str, Any] = {}
    for param in params:
        if param.optional:
            if param.name in args:
                supplimented_args[param.name] = args[param.name]
        else:
            if param.name not in args:
                raise KeyError(param.name)
            supplimented_args[param.name] = args[param.name]

    return Supplimented[O](callable_obj, **supplimented_args)