from dataclasses import dataclass

from vespwood_generator.schematic.schema import schema


@schema(name="ext_schema")
@dataclass
class ExtSchema:
    foo: str
    bar: int 

@schema(name="ext_array")
class ExtArray(list[ExtSchema]):
    ...

test_json_schema = {
    "type": "object",
    "properties": {
        "analysis": {
            "type": "string"
        },
        "change_required": {
            "type": "boolean"
        }
    }
}

expected_json_schema = {
    "type": "object",
        "properties": {
            "analysis": {
                "type": "string"
            },
            "change_required": {
                "type": "boolean"
            }
        },
    "required": ["analysis", "change_required"],
    "additionalProperties": False
}

load_value = { "analysis": "abc", "change_required": True }


asserts = { "change_required": True }