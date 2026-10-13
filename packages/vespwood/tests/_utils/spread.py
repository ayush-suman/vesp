from typing import overload, Any

class Spread(list[dict]):
    def __mul__(self, value: dict) -> "Spread":
        return [{**value, **term}for term in self]


@overload
def spread(param: str, table: list[Any]): ...
@overload
def spread(param: tuple[str, ...], table: list[tuple[Any, ...] | list[Any]]): ...

def spread(param: str | tuple[str, ...], table: list[Any] | list[tuple[Any, ...]]):
    if isinstance(param, tuple): 
        items = []
        for value in table:
            assert len(param) == len(value)
            items.append({param[idx]: v for idx, v in enumerate(value)})
        return Spread(items)
    return Spread([{param: value for value in table}])