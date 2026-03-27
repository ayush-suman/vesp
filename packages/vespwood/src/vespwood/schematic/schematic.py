from abc import ABC, abstractmethod
from enum import Enum
import inspect
from types import UnionType
from typing import Annotated, get_type_hints, get_origin, get_args, Union, List, Dict, Literal, Any
from typing_extensions import Doc
from vespwood._utils import setup_init


class Schematic(ABC):
    """
    A class that is the base class of Schema, Tool or Agent.
    Schematic has name, description and schema properties.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str | None:
        ...

    @property
    @abstractmethod
    def schema(self) -> dict[str, any]:
        """
        Get the parameters of the function as a JSON schema.

        :return: A dictionary representing the JSON schema of the function parameters.
        """
        ...

    @staticmethod
    def __type_to_json_schema(py_type, fallback):
        origin = get_origin(py_type)
        args = get_args(py_type)

        if origin is Annotated:
            py_type = args[0]
            doc: Doc | None
            if docs := list(filter(lambda a: isinstance(a, Doc), args[1:])):
                doc = docs[0]
            schema = Schematic.__type_to_json_schema(py_type, fallback)
            if doc:
                schema["description"] = doc.documentation
            return schema


        if origin is Literal:
            return {
                "enum": list(args)
            }

        if origin is Union or origin is UnionType:
            sub_schemas = [Schematic.__type_to_json_schema(arg, fallback) for arg in args]
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
                    "items": Schematic.__type_to_json_schema(item_type, fallback)
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
                "additionalProperties": Schematic.__type_to_json_schema(val_type, fallback)
            }

        if py_type in {int, float, str, bool}:
            return {"type": {
                int: "integer",
                float: "number",
                str: "string",
                bool: "boolean"
            }[py_type]}
        
        if inspect.isclass(py_type):
            if issubclass(py_type, Enum):
                return {
                    "enum": [m.value for m in py_type]
                }
            
            if Schematic in type(py_type).__mro__:
                return getattr(py_type, "schema")
        
        if fallback:
            return fallback(py_type, fallback)
        else:
            raise ValueError("Unkown type cannot be casted to json_schema without a fallback")
        
    @staticmethod
    def __class_to_json_schema(cls, fallback):
        json_schema = {"description": cls.__doc__} if cls.__doc__ else {}
        while (get_origin(cls) or cls) not in (int, float, str, bool, list, dict):
            cls = getattr(cls, "__orig_bases__")[0]
        json_schema.update(Schematic.__type_to_json_schema(cls, fallback))
        return json_schema


    @staticmethod
    def __any_to_json_schema(func, fallback=None):
        if inspect.isclass(func) and issubclass(func, (int, float, str, bool, list, dict)): 
            return Schematic.__class_to_json_schema(func, fallback or Schematic.__any_to_json_schema)

        sig = inspect.signature(func)
        type_hints = get_type_hints(func, include_extras=True)
        
        properties = {}
        required = []
        
        for name, _ in sig.parameters.items():
            py_type = type_hints.get(name, str)
            schema = Schematic.__type_to_json_schema(
                py_type, 
                fallback or Schematic.__any_to_json_schema
            )
            
            required.append(name)
            properties[name] = schema

        return {
            "type": "object",
            "description": func.__doc__, 
            "properties": properties,
            "required": required if required else [],
            "additionalProperties": False
        } if func.__doc__ else {
            "type": "object",
            "properties": properties,
            "required": required if required else [],
            "additionalProperties": False
        }


    @staticmethod
    def to_json_schema(obj):
        return Schematic.__any_to_json_schema(obj)


    @staticmethod
    def json_schema_to_type(json_schema: dict[str, Any], fallback):
        doc: Doc | None = None
        if "description" in json_schema:
            doc = Doc(json_schema["description"])

        if "enum" in json_schema:
            py_type = Literal[tuple(json_schema["enum"])]
            return Annotated[py_type, doc] if doc else py_type
        
        if "anyOf" in json_schema:
            py_type = Union[tuple(Schematic.json_schema_to_type(s, fallback) for i, s in enumerate(json_schema["anyOf"]))]
            return Annotated[py_type, doc] if doc else py_type
        
        if json_schema["type"] == "null":
            py_type = type(None)
            return Annotated[py_type, doc] if doc else py_type
        
        if json_schema["type"] == "array":
            py_type = list[Schematic.json_schema_to_type(json_schema["items"], fallback)]
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
                annotations[key] = Schematic.json_schema_to_type(
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