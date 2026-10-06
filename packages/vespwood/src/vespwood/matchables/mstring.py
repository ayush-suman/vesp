from __future__  import annotations
import re
from typing import Any
from vespwood._utils import parse_bool, format_map


class MString(str):
    def format_map(self, mapping) -> MString:
        string = format_map(self, mapping)
        return MString(string)


    def match(self, val: Any) -> bool:
        if isinstance(val, str):
            return bool(re.match(self, val))
        elif isinstance(val, bool):
            try:
                self = parse_bool(self)
            except:
                raise ValueError(f"Value is a boolean but match constraint {self} is not parseable to boolean")
            return self == val
        elif isinstance(val, int):
            try:
                self = int(self)
            except:
                raise ValueError(f"Value is an integer but match constraint {self} is not parseable to integer")
            return self == val
        return self == val