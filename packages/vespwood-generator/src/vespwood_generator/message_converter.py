from vespwood_generator.message import Message
from typing import Any
from collections.abc import Callable


def message_converter(func: Callable[[Message], dict[str, Any]] | None = None):
    def wrapper(f):
        def fn(prompts: list[Message]) -> list[dict[str, Any]]:
            converted_msgs = []
            for msg in prompts:
                converted_msgs.extend(f(msg))
            return converted_msgs
        return fn
    if func:
        return wrapper(func)
    else:
        return wrapper
    




