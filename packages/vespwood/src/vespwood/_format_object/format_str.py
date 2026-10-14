
from .format_object import FormatObject


class FormatStr(str, FormatObject): 
    @property
    def normalized(self) -> str:
        return str(self)
    
    @property
    def json(self) -> str:
        return str(self)
    
    def __format__(self, format_spec: str):        
        value = self
        match format_spec:
            case "count" | "length":
                return str(len(value))
            case _:
                value = super().__format__(format_spec)
        return value