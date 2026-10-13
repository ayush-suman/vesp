from typing import override


class Spread(list[dict]):
    def __mul__(self, value: dict) -> "Spread":
        return [{**value, **term}for term in self]


@override
def spread(param: str, table: tuple | list): ...
@override
def spread(param: tuple[str, str], table: dict): ...
@override
def spread(param: tuple[str], table: tuple[tuple | list]): ...
def spread(param: str | tuple, table: tuple | list | dict):
    if isinstance(table, dict):
        return Spread([{param[0]: key, param[1]: value} for key, value in table.items()])
    elif isinstance(param, tuple): 
        items = []
        for value in table:
            assert len(param) == len(value)
            items.append({param[idx]: v for idx, v in enumerate(value)})
        return Spread(items)
    return Spread([{param: value for value in table}])