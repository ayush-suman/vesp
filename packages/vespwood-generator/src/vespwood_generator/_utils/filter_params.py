import inspect
from typing import Any, get_type_hints
from dataclasses import dataclass

@dataclass
class Param:
    name: str
    type: type
    optional: bool = False


def filter_params(parameters: dict[str, inspect.Parameter], type_hints: dict[str, Any], skip_params: list[str], **args: dict[str, Any]) -> list[Param]:
    params = []
    for name, param in parameters.items():
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



