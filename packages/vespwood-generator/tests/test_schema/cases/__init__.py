from .case_1 import *
from .case_2 import *

cases = [
    {
        "test_json_schema": case_1.test_json_schema,
        "expected_json_schema": case_1.expected_json_schema,
        "schemas": [case_1.ExtSchema, case_1.ExtArray],
        "load_value": case_1.load_value,
        "asserts": case_1.asserts
    },
    {
        "test_json_schema": case_2.test_json_schema,
        "expected_json_schema": case_2.expected_json_schema,
        "schemas": [],
        "load_value": case_2.load_value,
        "asserts": case_2.asserts
    }
]