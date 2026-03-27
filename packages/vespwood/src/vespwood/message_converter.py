from vespwood.message import Prompt
from typing import Any
from collections.abc import Callable


def message_converter(func: Callable[[Prompt], dict[str, Any]] | None = None):
    def wrapper(f):
        def fn(prompts: list[Prompt]) -> list[dict[str, Any]]:
            converted_msgs = []
            for msg in prompts:
                converted_msgs.extend(f(msg))
            return converted_msgs
        return fn
    if func:
        return wrapper(func)
    else:
        return wrapper
    




