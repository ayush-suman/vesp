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
    
    def format(self, **kwargs):
        _val = self._val.format(**kwargs)
        return Expression(self.op, _val)

    def __str__(self):
        return f"{self.op} {self.val}"
    
    def __repr__(self):
        return f"{self.op} {self.val}"

