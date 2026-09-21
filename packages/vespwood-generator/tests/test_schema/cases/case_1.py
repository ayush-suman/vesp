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
        "a_int": {
            "type": "integer"
        },
        "b_anyOf": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "integer"
                }
            ]
        },
        "c_ext": {
            "type": "ext_schema"
        },
        "d_ext_arr": {
            "type": "ext_array"
        }
    }
}

expected_json_schema = {
    "type": "object",
    "properties": {
        "a_int": {
            "type": "integer"
        },
        "b_anyOf": {
            "anyOf": [
                {
                    "type": "string"
                },
                {
                    "type": "integer"
                }
            ]
        },
        "c_ext": {
            "type": "object",
            "description": 'ExtSchema(foo: str, bar: int)',
            "properties": {
                "foo": {
                    "type": "string"
                },
                "bar": {
                    "type": "integer"
                }
            },
            "required": ['foo', 'bar'], 
            "additionalProperties": False
        },
        "d_ext_arr": {
            "type": "array",
            "items": {
                "type": "object",
                "description": 'ExtSchema(foo: str, bar: int)',
                "properties": {
                    "foo": {
                        "type": "string"
                    },
                    "bar": {
                        "type": "integer"
                    }
                },
                "required": ['foo', 'bar'], 
                "additionalProperties": False
            }
        }
    },
    "required": ['a_int', 'b_anyOf', 'c_ext', 'd_ext_arr'],
    "additionalProperties": False
}

load_value = { "a_int": 1, "b_anyOf": "abc", "c_ext": { "foo": "xyz", "bar": 2 }, "d_ext_arr": []}

asserts = { "c_ext.foo": "xyz" }