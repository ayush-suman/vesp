from vespwood import PromptStructure, MessageList, Block, Schema, Structured
from vespwood.executors._prompt import _Prompt
import pathlib
import uuid
import pytest

@pytest.mark.parametrize(
    "file_name, args, responses, last_response_content", 
    [
        (
            "test_agent.json", 
            { "change_required": True }, 
            [
                Structured({ "analysis": "abc", "change_required": True }),
                Structured({ "analysis": "abc", "change_required": True }),
                Structured({ "analysis": "abc", "change_required": False }),
            ],
            ["Fail"]
        )
    ]
)
async def test_structure(file_name: str, args: dict, responses: list[Block | list[Block]], last_response_content: list[Block]):
    yaml_path = pathlib.Path(__file__).parent / file_name
    structure = PromptStructure.load_from_file(uuid.uuid4(), str(yaml_path))
    message_list = MessageList.from_prompt_structure(structure, args=args)
    for resp in responses:
        _, args, awaited_prompt = message_list.get_messages()
        id = awaited_prompt.id    
        awaited_prompt = _Prompt.from_prompt_unit(awaited_prompt, schemas=list(map(lambda s: Schema.from_json_schema(s["name"], s["json_schema"]), structure.schemas)))
        awaited_prompt.update_content(resp)
        print("Content", awaited_prompt.content)
        new_args = await awaited_prompt.invoke(None, args)
        message_list.update_content(id, resp, args=new_args)
        
    messages, args, awaited_prompt = message_list.get_messages()
    assert awaited_prompt == None
    assert messages[-1].content == last_response_content


