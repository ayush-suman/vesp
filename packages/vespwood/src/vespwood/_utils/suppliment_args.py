from typing import Any, get_type_hints, Generic, ParamSpec, TypeVar, Callable
from .filter_params import filter_params

I = ParamSpec("I")
O = TypeVar("O")
class SupplimentedCallable(Generic[I, O]):
    def __init__(self, callable_obj: Callable[I, O], **supplimented_args):
        self._callable = callable_obj
        self._supplimented_args = supplimented_args

    def __call__(self, *args: I.args, **kwargs) -> O:
        kwargs = self._supplimented_args | kwargs
        return self._callable(*args, **kwargs)


def suppliment_args(callable_obj: Callable[I, O], skip_params: list[str], **args: dict[str, Any]) -> SupplimentedCallable[I, O]:
    params = filter_params(callable_obj, skip_params, **args)
    supplimented_args: dict[str, Any] = {}
    for param in params:
        supplimented_args[param.name] = args[param.name]

    return SupplimentedCallable[I, O](callable_obj, **supplimented_args)