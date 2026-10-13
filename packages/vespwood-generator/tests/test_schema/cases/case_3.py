test_json_schema = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "string"
                    },
                    "b": {
                        "type": "integer"
                    },
                    "c": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                }
            }
        }
    }
}

expected_json_schema = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "a": {
                        "type": "string"
                    },
                    "b": {
                        "type": "integer"
                    },
                    "c": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    }
                },
                "additionalProperties": False,
                "required": ["a", "b", "c"]
            }
        }
    },
    "additionalProperties": False,
    "required": ["items"]
}

load_value = { "items": [{ "a": "abc", "b": 1, "c": ["xyz", "mno"]}]}

asserts = {}