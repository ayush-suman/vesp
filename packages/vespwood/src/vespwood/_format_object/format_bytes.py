from .format_object import FormatObject


class FormatBytes(bytes, FormatObject):
    def __format__(self, format_spec: str):
        match format_spec:
            case "utf-8":
                return self.decode()
            case "hex":
                return self.hex(sep=" ").upper()
            case "binary":
                return ''.join(f'{b:08b}' for b in self)
            case _:
                return super().__format__(format_spec)

    @property
    def normalized(self) -> bytes:
        return bytes(self)
    
    @property
    def json(self) -> str:
        return self.hex(' ')