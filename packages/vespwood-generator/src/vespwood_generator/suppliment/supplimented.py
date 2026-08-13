from typing import Any, Generic, ParamSpec, TypeVar, Callable

I = ParamSpec("I")
O = TypeVar("O")
class Supplimented(Generic[O]):
    def __init__(self, callable_obj: Callable[I, O], **supplimented_args):
        self._callable = callable_obj
        self._supplimented_args = supplimented_args

    def __call__(self, *args, **kwargs) -> O:
        kwargs = self._supplimented_args | kwargs
        return self._callable(*args, **kwargs)


