from .format_object import FormatObject


class FormatFloat(float, FormatObject):
    @property
    def normalized(self):
        return float(self)
