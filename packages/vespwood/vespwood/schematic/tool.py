from typing import Callable, Any
from .schematic import Schematic


class Tool[**I, O](Schematic):
    __slots__ = "_name", "_description", "_schema", "_function", "_caller",

    def __init__(self, func: Callable[I, O], *, name: str | None = None, description: str | None = None):
        self._name: str = name or func.__name__
        self._description: str | None = description or func.__doc__ or self.__doc__
        self._schema: dict[str, Any] | None = Schematic.to_json_schema(func) if func else None
        self._function: Callable[I, O] = func


    def update_with(self, *, name: str, description: str, schema: dict[str, Any]):
        if name:
            self.name = name
        if description:
            self.description = description
        if schema:
            self.schema = schema
        

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str | None:
        return self._description or self.__doc__
    
    @property
    def schema(self) -> dict[str, Any]:
        return self._schema
    

    def __call__(self, *args: I.args, **kwargs: I.kwargs) -> O:
        # TODO: look at self._function annotations and convert dicts to object
        return self._function(*args, **kwargs)



def tool(func: Callable | None = None, *, name: str | None = None, description: str | None = None) -> Tool:
    def wrapper(fn: Callable):
        return Tool(name=name, description=description, func=fn)
        
    if func:
        wrapper.__qualname__ = func.__qualname__
        wrapper.__name__ = func.__name__
        return wrapper(func) 
    else:
        return wrapper
    
