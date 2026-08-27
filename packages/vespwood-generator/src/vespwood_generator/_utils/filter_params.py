import inspect
from typing import Any, get_type_hints
from dataclasses import dataclass

@dataclass
class Param:
    name: str
    type: type
    optional: bool = False


def filter_params(callable_obj, skip_params: list[str], **args: dict[str, Any]) -> list[Param]:
    callable_obj = callable_obj if inspect.isfunction(callable_obj) or inspect.ismethod(callable_obj) else callable_obj.__call__
    sig = inspect.signature(callable_obj)
    type_hints = get_type_hints(getattr)
    params = []
    for name, param in sig.parameters.items():
        if name in skip_params:
            continue

        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue

        if param.kind == inspect.Parameter.VAR_KEYWORD:
            params = [Param(name=key, type=Any) for key in args]
            return params

        type = type_hints.get(name)
        params.append(Param(name, type, param.default is not inspect.Parameter.empty))
    return params



