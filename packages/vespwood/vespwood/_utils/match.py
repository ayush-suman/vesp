from typing import Any
import re

from vespwood.expression import Expression
from vespwood.logic import Logic


def match(val: Any, mval: Logic | Expression | Any):
    if isinstance(mval, Logic):
        assert len(mval.exprs) >= 2
        eval: bool
        if mval.conj == "and":
            eval = True
            for expr in mval.exprs:
                eval &= match(val, expr)
            return eval
        elif mval.conj == "or":
            eval = False
            for expr in mval.exprs:
                eval |= match(val, expr)
            return eval
        elif mval.conj == "xor":
            true_count = 0
            for expr in mval.exprs:
                if match(val, expr):
                    true_count += 1
                if true_count > 1:
                    return False
            return true_count == 1
        
    if isinstance(mval, Expression):
        op = mval.op
        match op:
            case ">" | "gt":
                return int(val) > int(mval.val)
            case ">=" | "gte":
                return int(val) >= int(mval.val)
            case "<" | "lt":
                print("Returning")
                return int(val) < int(mval.val)
            case "<=" | "lte":
                return int(val) <= int(mval.val)
            case "==" | "eq":
                return int(val) == int(mval.val)
            case "!=" | "not":
                return int(val) != int(mval.val)
            case _:
                raise ValueError("Unidentified operator passed in match")
            
    if isinstance(mval, str):
        return bool(re.match(mval, str(val)))
    elif mval is None:
        return bool(val)
    elif isinstance(mval, bool):
        return bool(val) == mval
    elif isinstance(mval, int):
        try:
            val = int(val)
        except:
            raise TypeError("Match value is integer but value is not parseable to integer")
        return val == mval
    return val == mval