from enum import Enum
from typing import Any, Callable, dataclass_transform, overload
from vespwood._utils import json_schema_to_type, to_json_schema, setup_init
from vespwood.errors import MissingSchemaError
from .schematic import Schematic


class Schema[T](type[T], Schematic):
    _name: str
    _description: str | None
    _schema: dict[str, Any]
    
    @property
    def name(cls): 
        return cls._name
    
    @property
    def description(cls): 
        return cls._description
    
    @property
    def schema(cls):
        return cls._schema


    def __new__(mcs, name, bases=(), ns={}, *, skip_init = False):
        cls = super().__new__(mcs, name, bases, ns)
        if getattr(cls, "_name", None) is None: cls._name = name
        if not hasattr(cls, "_description"): cls._description = None
        if not skip_init: cls = setup_init(cls)
        cls._schema = to_json_schema(cls)
        return cls
    

    @classmethod
    def from_json_schema(
        mcs,
        name: str,
        json_schema: dict[str, Any], 
        description: str | None = None, 
        schemas: list["Schema"] = [], 
        decorate_with: Callable[[type[T]], type[T]] | None = None
    ):
        def fallback(js):
            for s in schemas:
                if s.name == js["type"]:
                    s.__doc__ = js.get("description", s.__doc__)
                    return s
            raise MissingSchemaError([js["type"]])
        
        cls = None

        if "enum" in json_schema:
            cls = mcs(
                name,
                (Enum,),
                {"__enum__": json_type["enum"], "__doc__": json_schema["description"]},
                skip_init = True
            )
        
        if "anyOf" in json_schema:
            raise TypeError("anyOf at top level cannot be converted to a valid Schema")
        
        json_type = json_schema.get("type")

        if json_type == "array":
            py_type = json_schema_to_type(
                json_schema["items"],
                fallback
            )
            cls = mcs(
                name,
                (list[py_type],),
                {"__doc__": json_schema.get("description")},
                skip_init = True
            )
        
        if json_type in ("integer", "number", "string", "boolean"):
            py_type = {
                "integer": int,
                "number": float,
                "string": str,
                "boolean": bool
            }[json_schema["type"]]
            cls = mcs(
                name,
                (py_type,),
                {"__doc__": json_schema["description"]},
                skip_init = True
            )
        
        if json_type == "object":
            annotations = {}
            for key in json_schema["properties"]:
                annotations[key] = json_schema_to_type(
                    json_schema["properties"][key],
                    fallback
                )
            cls = mcs( 
                name, 
                (), 
                {"__annotations__": annotations, "__doc__": json_schema.get("description")},
                skip_init = True
            )
        
        if cls is None: cls = fallback(json_schema)

        if decorate_with: cls = decorate_with(cls)
        
        cls = setup_init(cls)

        if name: cls._name = name
        if description: cls._description = description
        cls._schema = to_json_schema(cls)

        return cls

    
    def __init__(cls, name, bases=(), ns={}, **kwargs):
        super().__init__(name, bases, ns, **kwargs)

    

@dataclass_transform(kw_only_default=True, frozen_default=True)
@overload
def schema[T](cls: type[T], /, *, name: str | None = None, description: str | None = None) -> Schema[T]: ...
@overload
def schema[T](cls: None = None, /, *, name: str | None = None, description: str | None = None) -> Callable[[type[T]], Schema[T]]: ...

def schema[T](cls: type[T] | None = None, /, *, name: str | None = None, description: str | None = None):
    def wrapper(cls) -> Schema[T]: 
        CombinedMeta = Schema
        if cls.__bases__:
            meta = [type(base) for base in cls.__bases__]
            CombinedMeta = type("Schema", (Schema, *meta), {})
        class Wrapper(cls, metaclass=CombinedMeta):
            _name = name
            _description = description
            __doc__ = cls.__doc__
            __name__ = cls.__name__
            __qualname__ = cls.__qualname__

        Wrapper.__class__.__name__ = cls.__class__.__name__
        Wrapper.__class__.__qualname__ = cls.__class__.__qualname__
        return Wrapper
    
    if cls is None:
        return wrapper
    return wrapper(cls)


    