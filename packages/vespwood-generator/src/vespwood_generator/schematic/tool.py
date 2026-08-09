from typing import Callable, Any, TypeVar, ParamSpec, Generic, Awaitable
from abc import abstractmethod
from vespwood_generator.schematic import Schematic


I = ParamSpec('I')
O = TypeVar('O')

class Tool(Schematic, Generic[I, O]):
    __slots__ = "_name", "_description", "_schema",


    def __init__(self, name: str | None = None, description: str | None = None, schema: Schematic | None = None):
        self._name: str = name or self.__class__.__name__
        self._description: str | None = description or self.__class__.__doc__
        self._schema: dict[str, Any] | None = schema.schema or Schematic.to_json_schema(self.__call__)


    def copy_with(self, *, name: str | None = None, description: str | None = None, schema: Schematic | None) -> "Tool": 
        return Tool(name or self.name, description or self.description, schema or self.schema)
        

    @property
    def name(self) -> str:
        return self._name
    

    @property
    def description(self) -> str | None:
        return self._description or self.__doc__
    

    @property
    def schema(self) -> dict[str, Any]:
        return self._schema
    
    @overload
    def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O: ...
    @overload
    def __call__(self, *args: I.args, **kwargs: I.kwargs) ->Awaitable[O]: ...
    @abstractmethod
    def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O | Awaitable[O]: ...


def tool(func: Callable[I, O] | None = None, *, name: str | None = None, description: str | None = None) -> Tool:
    def wrapper(fn: Callable):
        class WrapperTool(Tool[I, O]):
            def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O:
                return fn(*args, **kwargs)
            
        return WrapperTool(name=name, description=description, schema=Schematic.to_json_schema(fn))
        
    if func:
        wrapper.__qualname__ = func.__qualname__
        wrapper.__name__ = func.__name__
        return wrapper(func) 
    else:
        return wrapper
    
