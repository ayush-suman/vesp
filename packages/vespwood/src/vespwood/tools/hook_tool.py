from typing import Any, Callable, Generic, ParamSpec, TypeVar
from vespwood_generator import  Schematic, Tool
from vespwood.hook import Hook


I = ParamSpec("I")
O = TypeVar("O")
H = ParamSpec("H")
class HookTool(Tool[I, O], Generic[I, O, H]):
    def __init__(self, hook: Hook[H], name: str | None = None, description: str | None = None, schema: Schematic | None = None, ):
        self._hook = hook
        super().__init__(name, description, schema)

    @property
    def hook(self) -> Hook[H]:
        return self._hook

    def copy(self) -> "HookTool[I, O, H]":
        class CopiedTool(HookTool[I, O, H]):
            def __init__(inner_self):
                super().__init__(self._hook, self._name, self._description, self._schema)

            def __call__(inner_self, *args: I.args, **kwargs: I.kwargs) -> O:
                return self(*args, **kwargs)
        return CopiedTool()

    def copy_with(self, *, name = None, description = None, schema) -> "HookTool[I, O, H]":
        class CopiedTool(HookTool[I, O, H]):
            def __init__(inner_self):
                super().__init__(self._hook, name or self._name, description or self._description, schema or self._schema)

            def __call__(inner_self, *args: I.args, **kwargs: I.kwargs) -> O:
                return self(*args, **kwargs)
        return CopiedTool()


def hooktool(hook: Hook[H], *, name: str | None = None, description: str | None = None, schema: Schematic | None = None):
    def wrapper(fn: Callable[I, O]):
        class WrapperTool(HookTool[I, O, H]):
            def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O:
                return fn(*args, **kwargs)

        WrapperTool.__class__.__qualname__ = fn.__qualname__
        WrapperTool.__class__.__name__ = fn.__name__
        return WrapperTool(hook=hook, name=name or fn.__name__, description=description or fn.__doc__, schema=schema)
    return wrapper
    



        


        