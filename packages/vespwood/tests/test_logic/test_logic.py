from typing import Any

from vespwood.matchables.logic import Logic
from tests._utils.cases import with_cases
from tests.test_logic.cases import cases

@with_cases(cases)
async def test_logic_parsing(expr: str, value_table: list[tuple[Any, bool]]):
    logic = Logic.try_parse(expr)
    assert logic is not None
    for value in value_table:
        m = logic.match(value)
        assert m == value_table[value]
