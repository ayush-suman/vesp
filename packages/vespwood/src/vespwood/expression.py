from __future__ import annotations
import re

class Expression:
    __slots__ = "_op", "_val",

    def __init__(self, op: str, val: str):
        self._op = op
        self._val = val

    @classmethod
    def from_expr(cls, expr: str):
        op, val = re.split(r"\s+", expr)
        return cls(op, val)


    @property
    def op(self):
        return self._op
    
    @property
    def val(self):
        return self._val
    
    def format_map(self, mapping):
        _val = self._val.format_map(mapping)
        return Expression(self.op, _val)

    def __str__(self):
        return f"{self.op} {self.val}"
    
    def __repr__(self):
        return f"{self.op} {self.val}"
    


class BinaryExpression(Expression):
    def __init__(self, lval: str, op: str, val: str):
        self._lval = lval
        super().__init__(op, val)

    @classmethod
    def from_expr(cls, expr: str):
        lval, op, val = re.split(r"\s+", expr)
        return cls(lval, op, val)

    @property
    def left(self):
        return self._lval
    
    @property
    def op(self):
        return self._op
    
    @property
    def right(self):
        return self._val