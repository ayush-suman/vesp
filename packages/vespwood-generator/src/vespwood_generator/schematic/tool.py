from typing import Callable, Any, TypeVar, ParamSpec, Generic, Awaitable
from abc import abstractmethod
from vespwood_generator.schematic import Schematic, Schema


I = ParamSpec('I')
O = TypeVar('O')

class Tool(Schematic, Generic[I, O]):
    __slots__ = "_name", "_description", "_schema",

    def __init__(self, name: str | None = None, description: str | None = None, schema: Schematic | None = None):
        self._name: str = name or self.__class__.__name__
        self._description: str | None = description or self.__class__.__doc__
        self._schema: dict[str, Any] = schema.schema if schema else Schematic.to_json_schema(self.__call__)

    def copy(self) -> "Tool[I, O]":
        class CopiedTool(Tool[I, O]):
            def __init__(inner_self):
                super().__init__(self.name, self.description, Schema.from_json_schema(self.schema))

            def __call__(inner_self, *args: I.args, **kwargs: I.kwargs) -> O:
                return self(*args, **kwargs)
        return CopiedTool()

    def copy_with(self, *, name: str | None = None, description: str | None = None, schema: Schematic | None) -> "Tool[I, O]": 
        class CopiedTool(Tool[I, O]):
            def __init__(inner_self):
                super().__init__(name or self.name, description or self.description, Schema.from_json_schema(schema or self.schema))

            def __call__(inner_self, *args: I.args, **kwargs: I.kwargs) -> O:
                return self(*args, **kwargs)
        return CopiedTool()
        
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str | None:
        return self._description or self.__doc__
    
    @property
    def schema(self) -> dict[str, Any]:
        return self._schema

    @abstractmethod
    def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O: ...


def tool(func: Callable[I, O] | None = None, *, name: str | None = None, description: str | None = None) -> Tool:
    def wrapper(fn: Callable[I, O]):
        class WrapperTool(Tool[I, O]):
            def __init__(self, name = None, description = None, schema = None):
                self._name: str = name or fn.__name__
                self._description: str | None = description or fn.__doc__
                self._schema: dict[str, Any] = schema.schema if schema else Schematic.to_json_schema(fn)
                

            def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O:
                return fn(*args, **kwargs)
            
        return WrapperTool(name=name or fn.__name__, description=description or fn.__doc__)
        
    if func:
        wrapper.__qualname__ = func.__qualname__
        wrapper.__name__ = func.__name__
        return wrapper(func) 
    else:
        return wrapper
    
