from vespwood.matchables import Expression
from typing import Any
from tests.test_expression.cases import cases
from tests._utils.cases import with_cases

@with_cases(cases)
def test_expression(expr: str, value: Any, result: bool):
    expression = Expression.try_parse(expr)
    assert expression is not None
    assert result == expression.match(value)
