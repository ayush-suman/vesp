from enum import Enum
import inspect
from types import UnionType
from typing import Annotated, get_type_hints, get_origin, get_args, Union, List, Dict, Literal, Any
from typing_extensions import Doc
from .setup_init import setup_init
from vespwood.schematic import Schematic


def type_to_json_schema(py_type, fallback = None):
    origin = get_origin(py_type)
    args = get_args(py_type)

    if origin is Annotated:
        py_type = args[0]
        doc: Doc | None
        if docs := list(filter(lambda a: isinstance(a, Doc), args[1:])):
            doc = docs[0]
        schema = type_to_json_schema(py_type, fallback)
        if doc:
            schema["description"] = doc.documentation
        return schema


    if origin is Literal:
        return {
            "enum": list(args)
        }

    if origin is Union or origin is UnionType:
        sub_schemas = [type_to_json_schema(arg, fallback) for arg in args]
        schema = {}
        if len(sub_schemas) == 1:
            schema = sub_schemas[0]
        else:
            schema["anyOf"] = sub_schemas
        return schema

    if py_type is None or py_type is type(None):
        return {"type": "null"}

    if origin is list or origin is List or py_type is list:
        if args:
            item_type = args[0]
            schema = {
                "type": "array",
                "items": type_to_json_schema(item_type, fallback)
            }
        else:
            schema = {
                "type": "array",
                "items": {}
            }
        return schema

    if origin is dict or origin is Dict or py_type is dict:
        key_type, val_type = args if args else (str, str)
        if key_type != str:
            raise ValueError("JSON object keys must be strings")
        return {
            "type": "object",
            "additionalProperties": type_to_json_schema(val_type, fallback)
        }

    if py_type in {int, float, str, bool}:
        return {"type": {
            int: "integer",
            float: "number",
            str: "string",
            bool: "boolean"
        }[py_type]}
    
    if inspect.isclass(py_type):
        json_schema = {"description": py_type.__doc__} if py_type.__doc__ else {}
        if issubclass(py_type, Enum):
            json_schema.update({
                "enum": [m.value for m in py_type]
            })

        if Schematic in type(py_type).__mro__:
            return getattr(py_type, "schema")
    
    if fallback:
        return fallback(py_type, fallback)
    else:
        raise ValueError(f"{py_type} cannot be casted to json_schema without a fallback")


def to_json_schema(obj):
    if inspect.isclass(obj) and issubclass(obj, (int, float, str, bool, list, dict)): 
        json_schema = {"description": cls.__doc__} if cls.__doc__ else {}
        while (get_origin(cls) or cls) not in (int, float, str, bool, list, dict):
            cls = getattr(cls, "__orig_bases__")[0]
        json_schema.update(type_to_json_schema(cls, to_json_schema))
        return json_schema
    
    sig = inspect.signature(obj)
    type_hints = get_type_hints(obj, include_extras=True)
    
    properties = {}
    required = []
    
    for name, _ in sig.parameters.items():
        py_type = type_hints.get(name, str)
        schema = type_to_json_schema(
            py_type, 
            to_json_schema
        )
        
        required.append(name)
        properties[name] = schema

    return {
        "type": "object",
        "description": obj.__doc__, 
        "properties": properties,
        "required": required if required else [],
        "additionalProperties": False
    } if obj.__doc__ else {
        "type": "object",
        "properties": properties,
        "required": required if required else [],
        "additionalProperties": False
    }


def json_schema_to_type(json_schema: dict[str, Any], fallback):
    doc: Doc | None = None
    if "description" in json_schema:
        doc = Doc(json_schema["description"])

    if "enum" in json_schema:
        py_type = Literal[tuple(json_schema["enum"])]
        return Annotated[py_type, doc] if doc else py_type
    
    if "anyOf" in json_schema:
        py_type = Union[tuple(json_schema_to_type(s, fallback) for i, s in enumerate(json_schema["anyOf"]))]
        return Annotated[py_type, doc] if doc else py_type
    
    if json_schema["type"] == "null":
        py_type = type(None)
        return Annotated[py_type, doc] if doc else py_type
    
    if json_schema["type"] == "array":
        py_type = list[json_schema_to_type(json_schema["items"], fallback)]
        return Annotated[py_type, doc] if doc else py_type
    
    if json_schema["type"] in ("integer", "number", "string", "boolean"):
        py_type = {
            "integer": int,
            "number": float,
            "string": str,
            "boolean": bool
        }[json_schema["type"]]
        return Annotated[py_type, doc] if doc else py_type
    
    if json_schema["type"] == "object":
        annotations = {}
        for key in json_schema["properties"]:
            annotations[key] = json_schema_to_type(
                json_schema["properties"][key],
                fallback=fallback
            )  
        py_type = type( 
            "Object",
            (), 
            {"__annotations__": annotations, "__doc__": json_schema.get("description")}
        )
        py_type = setup_init(py_type)
        return Annotated[py_type, doc] if doc else py_type
    
    return fallback(json_schema)
