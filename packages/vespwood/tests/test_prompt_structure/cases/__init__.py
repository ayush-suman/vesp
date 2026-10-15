from vespwood_generator.blocks.structured import Structured
from vespwood_generator.message import Message

from tests._utils.spread import spread

_PRE = "cases/"

cases = [
    *spread(("responses", "last_response_content"),[
        (
            [
                Message("assistant", Structured({ "analysis": "abc", "change_required": True })),
                Message("assistant", Structured({ "analysis": "abc", "change_required": True })),
                Message("assistant", Structured({ "analysis": "abc", "change_required": False }))
            ], ["Fail"]
        )
    ]) * { "file_name": _PRE + "test_agent_1.json", "args": { "change_required": True }},
    *spread(("args", "last_response_content"), [
        ({ "index": 1, "given_index": 1 }, ["Entered"]),
        ({ "index": 1, "given_index": 2 }, ["Skipped"])
    ]
    ) * { "file_name": _PRE + "test_agent_2.json", "responses": []}
]