from typing import overload, SupportsIndex, Any

from .format_object import FormatObject


class FormatList(list[FormatObject | None], FormatObject):
    def __init__(self, value: list[FormatObject | None]):
        if not all(isinstance(v, FormatObject) for v in value if v is not None):
            raise ValueError("All elements of FormatList should be instances of FormatObject")
        super().__init__(value)


    def append(self, v: FormatObject | None) -> None:
        if v is not None and not isinstance(v, FormatObject):
            raise ValueError("Only instances of FormatObject can be appended to FormatList")
        super().append(v)


    def extend(self, it: list[FormatObject | None]) -> None:
        if not all(isinstance(v, FormatObject) for v in it if v is not None):
            raise ValueError("All elements of the iterable should be instances of FormatObject")
        super().extend(it)


    def insert(self, i: int, v: FormatObject | None) -> None:
        if v is not None and not isinstance(v, FormatObject):
            raise ValueError("Only instances of FormatObject can be inserted into FormatList")
        super().insert(i, v)


    @overload
    def __getitem__(self, i: str) -> Any: ...
    @overload
    def __getitem__(self, i: SupportsIndex) -> FormatObject | None: ...
    @overload
    def __getitem__(self, i: slice) -> list[FormatObject | None]: ...
    def __getitem__(self, i: str | SupportsIndex | slice) -> Any | FormatObject | None | list[FormatObject | None]:
        if isinstance(i, str):
            if "?" in i:
                idx, i = i.split("?", 1)
                try: idx = int(idx)
                except: raise TypeError("Key before ? should be an integer for FormatList objects")
                self = list.__getitem__(self, idx)    
            return FormatObject.__getitem__(self, i)
        return list.__getitem__(self, i)
    

    @overload
    def __setitem__(self, i: str, v: Any): ...
    @overload
    def __setitem__(self, i: SupportsIndex, v: FormatObject | None) -> None: ...
    @overload
    def __setitem__(self, i: slice, v: list[FormatObject | None]) -> None: ...
    def __setitem__(self, i: str | SupportsIndex | slice, v: Any | FormatObject | None | list[FormatObject | None]) -> None:
        if isinstance(i, str): 
            if "?" in i:
                idx, i = i.split("?", 1)
                try: idx = int(idx)
                except: raise TypeError("Key before ? should be an integer for FormatList objects")
                self = list.__getitem__(self, idx)    
            FormatObject.__setitem__(self, i, v)
        else:     
            if isinstance(i, slice):
                assert isinstance(v, list), "Value should be a list when assigning to a slice"
                if not all(isinstance(x, FormatObject) for x in v if x is not None):
                    raise ValueError("All elements of the list should be instances of FormatObject")
            elif isinstance(i, SupportsIndex):
                if v is not None and not isinstance(v, FormatObject):
                    raise ValueError("Only instances of FormatObject can be assigned to FormatList")
            list.__setitem__(self, i, v)


    @property
    def normalized(self) -> list[Any]:
        return [v.normalized if v is not None else None for v in self]
    

    @property
    def json(self) -> list[Any]:
        return [v.json if v is not None else None for v in self]
