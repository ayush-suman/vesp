from typing import Any
import uuid

from vespwood_generator import (
    Message,
    IndexedList
)

from ._format_object import FormatKeys, to_format_object
from .prompt_unit import PromptUnit
from .prompt_structure import PromptStructure


class MessageList(PromptStructure):
    _structures: IndexedList[PromptStructure, str]
    _message_id_map: dict[str, PromptUnit] = {}
    _format_keys: FormatKeys

    @classmethod
    def from_prompt_structure(cls, prompt_structure: PromptStructure, *, args: dict[str, Any] = {}, structures: IndexedList[PromptStructure, str] = IndexedList(key=lambda s: s.name)) -> "MessageList":
        self = cls(
            uuid.UUID(prompt_structure.id),
            prompt_list=prompt_structure.prompt_list,
            name=prompt_structure.name,
            description=prompt_structure.description,
            schemas=prompt_structure.schemas,
            tools=prompt_structure.tools,
            hooks=prompt_structure.hooks,
            validators=prompt_structure.validators,
            iterator=prompt_structure.iterator, 
            iter_key=prompt_structure.iter_key,
            initial=prompt_structure.initial,
            while_key=prompt_structure.while_key,
            if_key=prompt_structure.if_key,
            match=prompt_structure.match_key,
            else_list=prompt_structure.else_list,
            switch=prompt_structure.switch, 
            cases=prompt_structure.cases,
            params=prompt_structure.params
            
        )
        args = to_format_object(args)
        self._format_keys = args
        self._structures = structures
        return self


    @property
    def args(self) -> dict[str, Any]:
        return self._format_keys.normalized

    @property
    def structures(self) -> list[PromptStructure]:
        return self._structures
    

    def get_messages(self) -> tuple[list[Message], dict[str, Any], PromptUnit | None]:
        msgs, format_keys, awaited_prompt = self.hydrate(self._format_keys, message_id_map=self._message_id_map, structures=self._structures)
        return msgs, format_keys.normalized, awaited_prompt


    def update_message(self, id: str, message: Message, *, args: dict[str, Any] = {}):
        self._message_id_map[id] = message
        format_object = to_format_object(args)
        self._format_keys.update(format_object)


    def add_args(self, args: dict[str, Any]):
        args = to_format_object(args)
        self._format_keys.update(args)


    def __repr__(self):
        msgs, *_ = self.hydrate(self._format_keys, message_id_map=self._message_id_map, structures=self._structures)
        return str(msgs)
    

    def __str__(self):
        msgs, *_ = self.hydrate(self._format_keys, message_id_map=self._message_id_map, structures=self._structures)
        return str(msgs)        
