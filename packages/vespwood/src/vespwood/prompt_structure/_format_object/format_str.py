
from .format_object import FormatObject


class FormatStr(str, FormatObject): 
    @property
    def normalized(self):
        return str(self)