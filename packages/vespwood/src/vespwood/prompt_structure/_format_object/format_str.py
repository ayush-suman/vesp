
from .format_object import FormatObject


class FormatStr(str, FormatObject): 
    @property
    def normalized(self) -> str:
        return str(self)
    
    @property
    def json(self) -> str:
        return str(self)