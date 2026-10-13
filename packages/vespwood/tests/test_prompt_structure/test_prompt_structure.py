from typing import Any

from vespwood import PromptStructure, MessageList, Block, Schema
from vespwood.executors._prompt import _Prompt
from vespwood.prompt_structure._format_object import to_format_object
from tests.test_prompt_structure.cases import cases
from tests._utils.cases import with_cases
import pathlib
import uuid


@with_cases(cases)
async def test_structure(file_name: str, args: dict, responses: list[Block | list[Block]], last_response_content: list[Block]):
    yaml_path = pathlib.Path(__file__).parent / file_name
    structure = PromptStructure.load_from_file(uuid.uuid4(), str(yaml_path))
    message_list = MessageList.from_prompt_structure(structure, args=args)
    for resp in responses:
        _, args, awaited_prompt = message_list.get_messages()
        
        assert awaited_prompt is not None
        id = awaited_prompt.id    
        awaited_prompt = _Prompt.from_prompt_unit(awaited_prompt, schemas=list(map(lambda s: Schema.from_json_schema(s["name"], s["json_schema"]), structure.schemas)))
        awaited_prompt.update_content(resp)
        new_args = await awaited_prompt.invoke(None, args)
        message_list.update_content(id, resp, args=new_args)
        
    messages, args, awaited_prompt = message_list.get_messages()
    assert awaited_prompt == None
    assert messages[-1].content == last_response_content


# def test_match(file_name: str, args: dict, value_table: dict[Any, bool]):
#     ...
