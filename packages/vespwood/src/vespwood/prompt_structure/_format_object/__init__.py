from typing import Any, overload
from .format_object import FormatObject
from .format_bytes import FormatBytes
from .format_float import FormatFloat
from .format_int import FormatInt
from .format_list import FormatList
from .format_str import FormatStr
from .format_keys import FormatKeys


@overload
def to_format_object(data: None) -> None: ...
@overload
def to_format_object(data: dict[str, Any]) -> FormatKeys: ...
@overload
def to_format_object(data: list[Any]) -> FormatList: ...
@overload
def to_format_object(data: int) -> FormatInt: ...
@overload
def to_format_object(data: str) -> FormatStr: ...
@overload
def to_format_object(data: float) -> FormatFloat: ...
@overload
def to_format_object(data: bytes) -> FormatBytes: ...
def to_format_object(data: Any) -> FormatObject | None:
    if data is None: return None
    if isinstance(data, dict) and not isinstance(data, FormatKeys):
        return FormatKeys({k: to_format_object(v) for k, v in data.items()})
    if isinstance(data, list) and not isinstance(data, FormatList):
        return FormatList([to_format_object(v) for v in data])
    if isinstance(data, int) and not isinstance(data, FormatInt):
        return FormatInt(data)
    if isinstance(data, str) and not isinstance(data, FormatStr):
        return FormatStr(data)
    if isinstance(data, float) and not isinstance(data, FormatFloat):
        return FormatFloat(data)
    if isinstance(data, bytes) and not isinstance(data, FormatBytes):
        return FormatBytes(data)
    
    skip_types = (FormatInt, FormatFloat, FormatStr, FormatBytes, FormatKeys, FormatList)    
    if not isinstance(data, skip_types):
        cls = data.__class__
        fields = vars(data)
        return FormatKeys({name: to_format_object(getattr(data, name)) for name in fields}, extras={"__class__": cls, "__object__": data})
    return data


__all__ = [
    "FormatObject", 
    "FormatBytes", 
    "FormatFloat", 
    "FormatInt", 
    "FormatList", 
    "FormatStr", 
    "FormatKeys", 
    "to_format_object"
]