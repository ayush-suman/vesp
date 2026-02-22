from typing import Any

from vespwood.message import Message, Prompt, Response
from vespwood.tag import Tag
from vespwood.format_object import FormatKeys
from vespwood.types.schema_info import SchemaInfo
from vespwood.types.tools_list import ToolsList
from vespwood.types.hooks_list import HooksList
from vespwood.types.validators_list import ValidatorsList
from vespwood.types.saves import Saves

from .prompt_structure import Msgs, PromptStructure

class MessageList(PromptStructure):
    DEFAULT_LAST_TAG = "response_last"

    def __init__(self,
                prompt_list: list[Prompt | PromptStructure], 
                *,
                iterator: str | None = None, 
                iter_key: str | None = None,
                co_iterators: list[str] | None = None, 
                co_iter_keys: list[str | None] | None = None,
                default_co_iter_values: list[str | None] | None = None,
                initial: PromptStructure | None = None,
                whilekey: str | None = None,
                ifkey: str | list[str] | None = None,
                match: str | int | bool | None = None,
                then: PromptStructure | None = None,
                switch: str | None = None, 
                cases: list[PromptStructure] | None = None,
                **kwargs):
        super().__init__(
            prompt_list, 
            iterator=iterator, 
            iter_key=iter_key,
            co_iterators=co_iterators,
            co_iter_keys=co_iter_keys,
            default_co_iter_values=default_co_iter_values,
            initial=initial,
            whilekey=whilekey,
            ifkey=ifkey,
            match=match,
            then=then,
            switch=switch, 
            cases=cases,
        )
        self._format_keys: FormatKeys = FormatKeys(kwargs)
        self._tagged_messages: dict[str, Message] = {}


    @classmethod
    def from_prompt_structure(cls, prompt_structure: PromptStructure, *, keys: dict[str, Any] = {}, **kwargs) -> "MessageList":
        structure_dict = prompt_structure.as_dict
        structure_dict.update(kwargs)
        self = cls(prompt_structure, **structure_dict)
        self._format_keys.update(keys)
        return self
    

    @property
    def tagged_messages(self) -> dict[str, Message]:
        return self._tagged_messages
    

    @property
    def format_keys(self) -> FormatKeys:
        return self._format_keys
    

    def get_prompt_list(self) -> tuple[Msgs, Tag | None, SchemaInfo | None, ToolsList | None, HooksList | None, ValidatorsList | None, Saves | None]:
        msgs, tag, *rest = self.get_usables(self._format_keys, tagged_messages=self._tagged_messages)
        for prompt in msgs:
            if prompt.is_tagged:
                if prompt.tag not in self._tagged_messages:
                    self._tagged_messages[prompt.tag] = prompt

        # Adding default last message
        if tag is None and len(msgs) > 0 and msgs[-1].role != "assistant":
            tag = MessageList.DEFAULT_LAST_TAG
            prompt = Prompt.AWAITING_RESPONSE() @ tag
            if tag in self._tagged_messages:
                message = self._tagged_messages[tag]
                if message:
                    prompt.update_message(message)
                    if not prompt.response_awaited:
                        msgs.append(prompt)
                        return msgs, *([None] * 6)

        return msgs, tag, *rest
    

    def add_response(self, response: Response, *, keys: dict[str, Any] = {}):
        self._tagged_messages[response.tag] = response
        if any(isinstance(block, dict) for block in response):
            self.format_keys[response.tag] = list(filter(lambda b: isinstance(b, dict), response.content))[0]
        self._format_keys.update(keys)


    def update_message(self, tag: str, message: Message):
        if not tag in self._tagged_messages:
            raise ValueError(f"Tag {tag} not found in MessageList")
        self._tagged_messages[tag] = message
        self._format_keys[tag] = message.content


    def add_keys(self, keys: dict[str, Any]):
        self._format_keys.update(keys)


    def __repr__(self):
        msgs, *_ = self.get_usables(self._format_keys, tagged_messages=self._tagged_messages)
        return str(msgs)
    

    def __str__(self):
        msgs, *_ = self.get_usables(self._format_keys, tagged_messages=self._tagged_messages)
        return str(msgs)        





 
