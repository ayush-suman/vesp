from typing import Any
from .format_object import FormatObject


class FormatInt(int, FormatObject): 
    @property
    def normalized(self):
        return int(self)
