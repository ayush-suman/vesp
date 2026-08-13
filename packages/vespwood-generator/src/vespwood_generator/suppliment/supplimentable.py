from __future__ import annotations
from .suppliment import suppliment
from .supplimented import Supplimented


class Supplimentable:
    __skip_params__: list[str]

    def __class_getitem__(cls, skip_params: str | tuple[str, ...]) -> type[Supplimentable]:
        params = []
        if isinstance(skip_params, tuple):
            params = list(skip_params)
        else:
            params = [skip_params]
        return type(cls.__name__, (cls,), {"__skip_params__": params})
    
    
    def suppliment(self, **kwargs) -> Supplimented:
        return suppliment(self, skip_params=self.__class__.__skip_params__, **kwargs)
    