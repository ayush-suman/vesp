from typing import Any
from .format_object import FormatObject


class FormatInt(int, FormatObject): 
    @property
    def normalized(self) -> int:
        return int(self)
    
    @property
    def json(self) -> int:
        return int(self)
