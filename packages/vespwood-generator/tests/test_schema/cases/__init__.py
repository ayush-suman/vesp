from .case_1 import *

cases = [
    {
        "test_json_schema": case_1.test_json_schema,
        "expected_json_schema": case_1.expected_json_schema,
        "schemas": [case_1.ExtSchema, case_1.ExtArray],
        "load_value": case_1.load_value,
        "asserts": case_1.asserts
    }
]