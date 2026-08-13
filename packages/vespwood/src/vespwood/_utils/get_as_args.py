from typing import Any

def get_as_args(object, key: str) -> Any:
    if "." in key:
        attr, key = key.split(".", maxsplit=1)
        if isinstance(object, list):
            return list(map(lambda obj: get_as_args(object, attr)))
        object = object.get(attr) if isinstance(object, dict) else getattr(object, attr)
        return get_as_args(object, key)
    return object.get(key) if isinstance(object, dict) else getattr(object, key)