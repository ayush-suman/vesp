from __future__ import annotations
import re
from typing import Any, Literal, TypeAlias
from .matchable import Matchable
from .mstring import MString


OpType: TypeAlias = Literal[">", "<", ">=", "<=", "!=", "==", "gt", "lt", "gte", "lte", "eq", "not"]

class Expression(Matchable):
    __slots__ = "_op", "_val",

    def __init__(self, op: OpType, val: str):
        self._op = op
        self._val = MString(val)

    @classmethod
    def try_parse(cls, expr: str) -> Expression | None:
        expr = expr.strip()
        match = re.match(r"(?P<op>>=|<=|==|!=|>|<|\b(?:gte|lte|gt|lt|eq|not)\b)\s*(?P<val>\S+)$", expr)
        if match is None: 
            return None
        match_dict = match.groupdict()
        if "op" not in match_dict or "val" not in match_dict:
            return None
        return cls(match_dict["op"], match_dict["val"])

    @classmethod
    def parse(cls, expr: str) -> Expression:
        parsed = Expression.try_parse(expr)
        if parsed is None:
            raise ValueError(f'Given string {expr} is not parseable to Expression')
        return parsed

    @property
    def op(self) -> OpType:
        return self._op
    
    @property
    def val(self) -> str:
        return self._val
    
    def format_map(self, mapping: dict[str, Any]) -> Expression:
        _val = self._val.format_map(mapping)
        return Expression(self.op, _val)

    def match(self, val) -> bool:
        op = self.op
        match op:
            case ">" | "gt":
                return int(val) > int(self.val)
            case ">=" | "gte":
                return int(val) >= int(self.val)
            case "<" | "lt":
                return int(val) < int(self.val)
            case "<=" | "lte":
                return int(val) <= int(self.val)
            case "==" | "eq":
                return int(val) == int(self.val)
            case "!=" | "not":
                return int(val) != int(self.val)
            case _:
                raise ValueError("Unidentified operator passed in match")

    def __str__(self):
        return f"{self.op} {self.val}"
        
    def __repr__(self):
        return f"{self.op} {self.val}"
    
