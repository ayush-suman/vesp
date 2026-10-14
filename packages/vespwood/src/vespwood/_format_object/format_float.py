from .format_object import FormatObject


class FormatFloat(float, FormatObject):
    @property
    def normalized(self) -> float:
        return float(self)
    
    @property
    def json(self) -> float:
        return float(self)
