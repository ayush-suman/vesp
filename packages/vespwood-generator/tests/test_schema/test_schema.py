
from typing import Any
import operator
from vespwood_generator.schematic.schema import Schema
from tests.test_schema.cases import cases
from tests._utils.cases import with_cases


@with_cases(cases)
def test_schema_init(test_json_schema, schemas, expected_json_schema):
    schema = Schema.from_json_schema("TestSchema", test_json_schema, schemas=schemas)
    assert schema.schema == expected_json_schema

    
@with_cases(cases)
def test_schema_load(test_json_schema, schemas, load_value, asserts: dict[str, Any]):
    schema = Schema.from_json_schema("TestSchema", test_json_schema, schemas=schemas)
    obj = schema.load(load_value)
    for key, value in asserts.items():
        assert operator.attrgetter(key)(obj) == value



