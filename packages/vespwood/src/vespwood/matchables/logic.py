from __future__ import annotations
from typing import Any, Literal, TypeAlias
import re
from vespwood._utils import format_map
from vespwood.matchables.mstring import MString
from .expression import Expression
from .matchable import Matchable


ConjType: TypeAlias = Literal['&', '|', '^']


def _precedence_of(conj: ConjType | None) -> Literal[0, 1, 2]:
    match conj:
        case '&': return 2
        case '^': return 1
        case '|': return 0
        case None: return -1
        case _: raise ValueError("Not a valid conjugate for logic")


_ConjParseStates: TypeAlias = Literal[256, 128, 64, 32, 16, 8, 4, 2, 1, 0]


class _ConjParseSM:
    START_STATE = 0b1 << 8
    A_STATE = START_STATE >> 1
    AN_STATE = START_STATE >> 2
    AND_STATE = START_STATE >> 3
    X_STATE = START_STATE >> 4
    XO_STATE = START_STATE >> 5
    XOR_STATE = START_STATE >> 6
    O_STATE = START_STATE >> 7
    OR_STATE = START_STATE >> 8
    NULL_STATE = 0
    FIN_STATE = -1

    @staticmethod
    def resolve_next(current_state: _ConjParseStates, char: str) -> tuple[_ConjParseStates, ConjType | None]:
        next_state = _ConjParseSM.NULL_STATE
        if char == '&' or char == '^' or char == '|':
            return _ConjParseSM.FIN_STATE, char
        if char == ' ':
            if current_state == _ConjParseSM.AND_STATE: return _ConjParseSM.FIN_STATE, '&'
            elif current_state == _ConjParseSM.XOR_STATE: return _ConjParseSM.FIN_STATE, '^'
            elif current_state == _ConjParseSM.OR_STATE: return _ConjParseSM.FIN_STATE, '|'
            return _ConjParseSM.START_STATE, None
        match current_state:
            case _ConjParseSM.START_STATE:
                match char:
                    case 'a': next_state = _ConjParseSM.A_STATE
                    case 'x': next_state = _ConjParseSM.X_STATE
                    case 'o': next_state = _ConjParseSM.O_STATE
                    case _: next_state = _ConjParseSM.NULL_STATE
            case _ConjParseSM.A_STATE:
                next_state = _ConjParseSM.AN_STATE if char == 'n' else _ConjParseSM.NULL_STATE
            case _ConjParseSM.AN_STATE:
                next_state = _ConjParseSM.AND_STATE if char == 'd' else _ConjParseSM.NULL_STATE
            case _ConjParseSM.X_STATE:
                next_state = _ConjParseSM.XO_STATE if char == 'o' else _ConjParseSM.NULL_STATE
            case _ConjParseSM.XO_STATE:
                next_state = _ConjParseSM.XOR_STATE if char == 'r' else _ConjParseSM.NULL_STATE
            case _ConjParseSM.O_STATE:
                next_state = _ConjParseSM.OR_STATE if char == 'r' else _ConjParseSM.NULL_STATE
            case _:
                next_state = _ConjParseSM.NULL_STATE
        
        return next_state, None                


class Logic(Matchable):
    __slots__ = "_conj", "_exprs",

    def __init__(self, conj: ConjType, val1: Matchable | str, val2: Matchable | str):
        self._conj = conj
        def if_str(val: str) -> Matchable:
            parsed = Logic.try_parse(val)
            if parsed is None:
                parsed = Expression.try_parse(val)
                if parsed is None:
                    parsed = MString(val)
        self._val1 = if_str(val1) if isinstance(val1, str) and isinstance(val1, Matchable) else val1
        self._val2 = if_str(val2) if isinstance(val2, str) and isinstance(val2, Matchable) else val2


    @classmethod
    def try_parse(cls, expr: str) -> Logic | None:
        expr = expr.strip()
        def resolve(expression: str) -> tuple[Logic | None, int]:
            e = None
            expr_stack = []
            conj_stack = []
            state = _ConjParseSM.NULL_STATE
            start = 0
            end = 0
            expr_len = len(expression)
            i = 0
            while i < expr_len:
                print(i, expr_len)
                if expression[i] == '(':
                    expr_part, *_ = expression[i + 1:].rsplit(')', maxsplit=1)
                    e, skip = resolve(expr_part)
                    i += skip 
                else:
                    state, conj = _ConjParseSM.resolve_next(state, expression[i])
                    if state == _ConjParseSM.NULL_STATE: end = i + 1
                    elif state == _ConjParseSM.START_STATE: end = i
                    if state == _ConjParseSM.FIN_STATE:
                        if e is None:
                            e = expression[start:end]
                            e = Expression.try_parse(e) or MString(e)
                        while len(conj_stack) > 0:
                            if _precedence_of(conj_stack[-1]) >= _precedence_of(conj):
                                e = Logic(conj_stack.pop(), expr_stack.pop(), e)
                            else:
                                break
                        expr_stack.append(e)
                        conj_stack.append(conj)
                        start = i + 1
                        end = start
                        e = None
                    i += 1
            if e is None:
                e = expression[start:end + 1]
                e = Expression.try_parse(e) or MString(e)
            while len(conj_stack) > 0:
                e = Logic(conj_stack.pop(), expr_stack.pop(), e)
            return e, i
        logic, _ = resolve(expr)
        return logic

    @property
    def conj(self) -> ConjType:
        return self._conj

    @property
    def va1(self) -> Matchable:
        return self._val1

    @property
    def val2(self) -> Matchable:
        return self._val2
    
    def format_map(self, mapping) -> Logic:
        return Logic(self.conj, self._val1.format_map(mapping), self._val2.format_map(mapping))

    def match(self, val: Any) -> bool:
        match1 = self._val1.match(val)
        match2 = self._val2.match(val)
        match self._conj:
            case '&': return match1 and match2
            case '^': return (match1 or match2) and not (match1 and match2) 
            case '|': return match1 or match2    
    
    def __str__(self):
        return str({"conj": self.conj, "val1": self._val1, "val2": self._val2 })
    
    def __repr__(self):
        return str({"conj": self.conj, "val1": self._val1, "val2": self._val2 })

    

    