from __future__ import annotations
from enum import Enum
import enum
import inspect
import types
import datetime as dt
from typing import Any, Callable, Union, dataclass_transform, get_args, get_origin, overload, Generic, TypeVar, get_type_hints
from vespwood_generator._utils import setup_init
from vespwood_generator.schematic import Schematic
from vespwood_generator.indexed_list import IndexedList


T = TypeVar('T')
class Schema(type[T], Schematic, Generic[T]):
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
        _name = ns.pop("_name", None)
        _description = ns.pop("_description", None)
        cls = super().__new__(mcs, name, bases, ns)
        cls._name = _name or name
        cls._description = _description or None
        if not skip_init: cls = setup_init(cls)
        cls._schema = Schematic.to_json_schema(cls)
        return cls
    

    @classmethod
    def from_json_schema(
        mcs,
        name: str,
        json_schema: dict[str, Any], 
        description: str | None = None, 
        schemas: IndexedList["Schema", str] = IndexedList["Schema", str](key=lambda s: s.name), 
        decorate_with: Callable[[type[T]], type[T]] | None = None
    ):
        def fallback(js):
            s = schemas.find(js["type"])
            if s is None:
                return KeyError(js["type"])

            s.__doc__ = js.get("description", s.__doc__)
            return s
        
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
            py_type = Schematic.json_schema_to_type(
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
                annotations[key] = Schematic.json_schema_to_type(
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
        cls._schema = Schematic.to_json_schema(cls)

        return cls

    
    def __init__(cls, name, bases=(), ns={}, **kwargs):
        super().__init__(name, bases, ns, **kwargs)


    def load(cls, data: dict[str, Any]) -> T:
        def load_values(tp, payload: Any):
            if tp is Any:
                return payload

            origin = get_origin(tp)
            if origin is not None:
                args = get_args(tp)
                if origin in (Union, types.UnionType):
                    opts = [a for a in args if a is not type(None)]
                    if payload is None:
                        return None
                    for a in opts:
                        try:
                            return load_values(a, payload)
                        except Exception:
                            pass
                    raise TypeError(f"no union member of {tp} fits {payload!r}")
                if origin in (list, set, frozenset):
                    return origin(load_values(args[0], v) for v in payload)
                if origin is tuple:
                    if len(args) == 2 and args[1] is Ellipsis:
                        return tuple(load_values(args[0], v) for v in payload)
                    return tuple(load_values(a, v) for a, v in zip(args, payload))
                if origin is dict:
                    kt, vt = args
                    return {load_values(kt, k): load_values(vt, v) for k, v in payload.items()}
                tp = origin          

            if inspect.isclass(tp):
                if tp is type(None):
                    return None
                if issubclass(tp, enum.Enum):
                    return tp(payload)
                if tp in (dt.datetime, dt.date, dt.time):
                    return tp.fromisoformat(payload)
                if tp in (int, float, str, bool):
                    if not isinstance(payload, tp):
                        raise TypeError(f"expected {tp.__name__}, got {payload!r}")
                    return payload
                
            signature = inspect.signature(tp)
            type_hints = get_type_hints(tp, include_extras=True)

            args = {}
            for name, _ in signature.parameters.items():
                py_type = type_hints.get(name, str)
                args[name] = load_values(py_type, payload[name])

            return tp(**args)
        
        return load_values(cls, data)


S = TypeVar("S")    

@dataclass_transform(kw_only_default=True, frozen_default=True)
@overload
def schema(cls: type[S], /, *, name: str | None = None, description: str | None = None) -> Schema[S]: ...
@overload
def schema(cls: None = None, /, *, name: str | None = None, description: str | None = None) -> Callable[[type[S]], Schema[S]]: ...

def schema(cls: type[S] | None = None, /, *, name: str | None = None, description: str | None = None):
    def wrapper(cls) -> Schema[S]: 
        CombinedMeta = Schema
        if cls.__bases__:
            meta = [base.__class__ for base in cls.__bases__]
            if not any(Schema in m.__mro__ for m in meta):
                CombinedMeta = type("Schema", (Schema, *meta), {})
            else: 
                CombinedMeta = type("Schema", tuple(meta), {})
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


    