from __future__ import annotations
from typing import Any, Literal
from .expression import Expression


class Logic:
    __slots__ = "_conj", "_exprs",

    def __init__(self, conj: Literal["and", "or", "xor"], exprs: list[Logic | Expression | Any]):
        self._conj = conj
        self._exprs = exprs

    @classmethod
    def from_dict(cls, data: dict):
        assert len(data) == 1
        conj = data.keys()[0]
        exprs = data[conj]
        return cls(conj, exprs)

    @property
    def conj(self):
        return self._conj
    
    @property
    def exprs(self):
        return self._exprs
    
    def format(self, **kwargs):
        _exprs = []
        for expr in self.exprs:
            if isinstance(expr, str) or isinstance(expr, Expression) or isinstance(expr, Logic):
                _exprs.append(expr.format(**kwargs))
            else:
                _exprs.append(expr)
        return Logic(self.conj, _exprs)
    
    def __str__(self):
        return str({"conj": self.conj, "expressions": self.exprs })
    
    def __repr__(self):
        return str({"conj": self.conj, "expressions": self.exprs })