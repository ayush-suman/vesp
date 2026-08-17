from typing import Any, overload

from vespwood_generator import (
    Message
)
from vespwood.types import (
    Params,
    SchemaList,
    ToolsList, 
    HooksList, 
    ValidatorsList, 
    Saves
)

from vespwood.prompt import Prompt
from vespwood.tag import Tag
from ._format_object import FormatKeys, to_format_object
from .prompt_structure import PromptStructure
from vespwood.logic import Logic
from vespwood.expression import Expression


class MessageList(PromptStructure):

    @overload
    def __init__(
        self,
        id: str,
        *,
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        **kwargs
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        iterator: str, 
        prompt_list: list[Prompt | PromptStructure | str],
        initial: list[Prompt | PromptStructure | str] | None = None,
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        iter_key: str | None = None,
        index_key: str | None = None,
        params: Params | None = None,
        **kwargs
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        while_key: str,
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        initial: list[Prompt | PromptStructure | str] | None = None,
        match: str | int | bool | dict | Logic | Expression | None = None,
        index_key: str | None = None,
        params: Params | None = None,
        **kwargs
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        if_key: str,
        prompt_list: list[Prompt | PromptStructure | str],
        else_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        match: str | int | bool | dict | Logic | Expression | None = None,
        params: Params | None = None,
        **kwargs
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        cases: list[PromptStructure | str],
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        switch: str | None = None, 
        params: Params | None = None,
        **kwargs
    ): ...
    @overload
    def __init__(
        self,
        id: str,
        *,
        match: str | int | bool | dict | Logic | Expression | None,
        prompt_list: list[Prompt | PromptStructure | str],
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        params: Params | None = None,
        **kwargs
    ): ...
    def __init__(
        self,
        id: str,
        *,
        prompt_list: list[Prompt | PromptStructure | str],
        iterator: str | None = None,
        while_key: str | None = None,
        if_key: str | None = None,
        cases: list[PromptStructure | str] | None = None,
        match: str | int | bool | dict | Logic | Expression | None = None,
        else_list: list[Prompt | PromptStructure | str] | None = None,
        initial: list[Prompt | PromptStructure | str] | None = None,
        iter_key: str | None = None,
        index_key: str | None = None,
        switch: str | None = None,
        name: str | None = None,
        description: str | None = None,
        schemas: SchemaList | None = None,
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        params: Params | None = None,
        **kwargs
    ):
        super().__init__(
            prompt_list, 
            id=id,
            name=name,
            description=description,
            schemas=schemas,
            tools=tools,
            hooks=hooks,
            validators=validators,
            iterator=iterator, 
            iter_key=iter_key,
            index_key=index_key,
            initial=initial,
            while_key=while_key,
            if_key=if_key,
            match=match,
            else_list=else_list,
            switch=switch, 
            cases=cases,
            params=params
        )
        self._format_keys: FormatKeys = to_format_object(kwargs)
        self._prompt_id_map: dict[str, Prompt] = {}


    @classmethod
    def from_prompt_structure(cls, prompt_structure: PromptStructure, *, args: dict[str, Any] = {}) -> "MessageList":
        self = cls(
            prompt_structure.id,
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
        self._format_keys.update(args)
        return self


    @property
    def args(self) -> dict[str, Any]:
        return self._format_keys.normalized
    

    def get_prompt_list(self) -> tuple[list[Message], dict[str, Any], Prompt | None]:
        msgs, format_keys, awaited_prompt = self.get_usables(self._format_keys, message_id_map=self._prompt_id_map)
        return msgs, format_keys.normalized, awaited_prompt


    def update_message(self, id: str, message: Message, *, args: dict[str, Any] = {}):
        self._prompt_id_map[id] = message
        if any(isinstance(block, dict) for block in message.content):
            self._format_keys[message.tag] = to_format_object(list(filter(lambda b: isinstance(b, dict), message.content))[0])
        keys = to_format_object(message.saved_args)
        self._format_keys.update(keys)


    def add_args(self, args: dict[str, Any]):
        args = to_format_object(args)
        self._format_keys.update(args)


    def __repr__(self):
        msgs, *_ = self.get_usables(self._format_keys, message_id_map=self._prompt_id_map)
        return str(msgs)
    

    def __str__(self):
        msgs, *_ = self.get_usables(self._format_keys, message_id_map=self._prompt_id_map)
        return str(msgs)        
