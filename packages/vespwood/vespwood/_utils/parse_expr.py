import re
from typing import Any, Literal
from vespwood.expression import Expression
from vespwood.logic import Logic


def get_conj_and_exprs(mval: str) -> tuple[Literal["and", "or", "xor", "expr"] | str, list[str]]:
    and_parts = re.split(r"[\s+|)]and[\s+|(]", mval)
    or_parts = re.split(r"[\s+|)]or[\s+|(]", mval)
    xor_parts = re.split(r"[\s+|)]xor[\s+|(]", mval)
    if len(and_parts) > 1:
        assert len(or_parts) == 1
        assert len(xor_parts) == 1
        return "and", and_parts
    if len(or_parts) > 1:
        assert len(and_parts) == 1
        assert len(xor_parts) == 1
        return "or", or_parts
    if len(xor_parts) > 1:
        assert len(and_parts) == 1
        assert len(or_parts) == 1
        return "xor", xor_parts
    if re.findall(r"(?:!=|[<>]=?|~|[gl]te?|eq|not)\s*", mval):
        return "expr", [mval]
    else:
        return "", [mval]


def parse_exprs(mval: str, *, brackets=None) -> Logic | Expression | Any:
    if mval.startswith("(") and mval.endswith(")"):
        if brackets is not None:
            raise SyntaxError("Something is not right with expression", mval)
        mval = mval.strip("(")
        mval = mval.strip(")")

    if isinstance(brackets, list):
        if len(brackets) == 0:
            conj, exprs = get_conj_and_exprs(mval)
            if conj == "expr":
                return Expression.from_expr(exprs[0])
            elif conj == "":
                return exprs[0]
            return Logic(conj, exprs)
        parts = []
        conj_start, exprs_start = get_conj_and_exprs(mval[:brackets[0][0]])
        conj_end, exprs_end = get_conj_and_exprs(mval[brackets[-1][-1]:])
        assert conj_start == conj_end
        parts.extend(exprs_start[:-1])
        parts.extend(exprs_end[1:])
        parts = list(map(Expression.from_expr, parts))
        for bra in brackets:
            start = bra[0] + 1
            end = bra[-1] 
            m = mval[start:end]
            if len(bra) == 2:
                parts.append(parse_exprs(m, brackets=[]))
            else:
                parts.append(parse_exprs(m, brackets=bra[1:-1]))
        return Logic(conj_start, parts)
        
    match_list = re.findall(r"(?:!=|[<>]=?|~|[gl]te?|eq|not)\s*[{]?\w+[}]?", mval)
    match(len(match_list)):
        case 0:
            return mval
        case 1:
            return Expression.from_expr(match_list[0])
        case _:
            if brackets is None:
                brackets = [0]
                indices = []
                for i, c in enumerate(mval):
                    if c == "(":
                        at = brackets
                        for idx in indices:
                            at = at[idx]
                        indices.append(len(at))
                        offset = 0
                        if len(at):
                            offset = at[0]
                        at.append([i - offset])
                    if c == ")": 
                        at = brackets
                        for idx in indices:
                            offset = 0
                            if len(at):
                                offset = at[0]
                            at = at[idx]
                        at.append(i - offset)
                        indices.pop()
            return parse_exprs(mval, brackets=brackets[1:])
        

def parse_dict(mval: dict) -> Logic | str:
    assert len(mval) == 1
    conj = list(mval.keys())[0]
    if conj not in ["and", "or", "xor"]:
        return "{" + f"{conj}" + "}"
    exprs = mval[conj]
    parsed_exprs = []
    for expr in exprs:
        if isinstance(expr, str):
            parsed_exprs.append(parse_exprs(expr))
        elif isinstance(exprs, dict):
            parsed_exprs.append(parse_dict(expr))
        else:
            parsed_exprs.append(expr)
    return Logic(conj, parsed_exprs)