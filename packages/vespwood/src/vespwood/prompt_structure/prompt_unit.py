from __future__ import annotations
from enum import Enum
from typing import Self
import uuid

from vespwood.tag import Tag
from vespwood.types.hooks import HooksList
from vespwood.types.params import Params
from vespwood.types.saves import Saves
from vespwood.types.schema import SchemaInfo
from vespwood.types.tools import ToolsList
from vespwood.types.validators import ValidatorsList
from vespwood_generator.blocks import Block, Image, File, ToolCall
from vespwood_generator.blocks.structured import Structured
from vespwood_generator.message import Message
from vespwood_generator.types.role import Role


class PromptUnit(Message):
    __slots__ = "_id", "_tag", "_params", "_schema", "_tools", "_hooks", "_validators", "_saves"
    
    def __init__(
        self, 
        id: uuid.UUID,
        *,
        role: Role, 
        content: Block | list[Block] | None = None, 
        params: Params | None = None, 
        schema: SchemaInfo | None = None, 
        tools: ToolsList | None = None,
        hooks: HooksList | None = None,
        validators: ValidatorsList | None = None,
        saves: Saves | None = None,
        tag: str | None = None
    ):
        self._id: uuid.UUID = id
        self._params: Params | None = params
        self._schema: SchemaInfo | None = schema
        self._tools: ToolsList | None = tools
        self._hooks: HooksList | None = hooks
        self._validators: ValidatorsList | None = validators
        self._saves: Saves | None = saves
        self._tag: Tag | None = Tag(tag) if tag else None
        super().__init__(role, content)


    @classmethod
    def load_from_dict(cls, id: uuid.UUID, data: dict):
        def convert(content: str | dict) -> str | dict:
            if isinstance(content, str):
                return content.strip()
            elif isinstance(content, dict):
                if "image" in content:
                    return Image(**content["image"])
                elif "file" in content:
                    return File(**content["file"])
                elif "structured" in content:
                    return content["structured"]  
                elif "tool" in content:
                    return ToolCall(**content["tool"])
        
        role = None
        content = None
        
        roles = ["user", "system", "assistant"]
        for r in roles:
            if r in data:
                content = data.get(r)
                if content:
                    if isinstance(content, list):
                        content = list(map(convert, content))
                    else:
                        content = [convert(content)]
                role = r
                break

        params = data.get("params")
        schema = data.get("schema")
        tools = data.get("tools")
        hooks = data.get("hooks")
        validators = data.get("validators")
        saves = data.get("saves")
        tag = data.get("tag")
        prompt = cls(
            id,
            role=role,
            content=content, 
            params=params, 
            schema=schema, 
            tools=tools, 
            hooks=hooks, 
            validators=validators, 
            saves=saves,
            tag=tag
        )
        return prompt

    
    def update_content(self, content: Block | list[Block]):
            if content is None:
                self._content = None
            elif isinstance(content, (str, Structured, ToolCall, Image, File)):
                self._content = [content]
            elif isinstance(content, list):
                self._content = content

    def indexed(self, idx) -> Self:
        self = super().indexed(idx)
        if self.is_tagged:
            self._tag = self._tag.indexed(idx)
        return self

    def copy(self):
        prompt = PromptUnit(
            self._id,
            role=self._role, 
            content=self._content.copy() if self._content else None, 
            params=self._params.copy() if self._params else None,
            schema=self._schema.copy() if isinstance(self._schema, dict) else self._schema,
            tools=self._tools.copy() if self._tools else None,
            hooks=self._hooks.copy() if self._hooks else None,
            validators=self._validators.copy() if self._validators else None,
            saves=self._saves.copy() if self._saves else None,
            tag=self._tag.copy() if self._tag else None
        )
        return prompt

    
    def __copy__(self):
        return self.copy()

    
    def format_map(self, prompt_mapping) -> PromptUnit:
        prompt = self.copy()
        if prompt._content: 
            content = []
            for block in prompt._content:
                if isinstance(block, str):
                    block = block.format_map(prompt_mapping)
                content.append(block)
            prompt._content = content
        if prompt._hooks:
            hooks = []
            for hook in prompt._hooks:
                if isinstance(hook, str):
                    hooks.append(hook.format_map(prompt_mapping))
                else:
                    hook = {
                        "name": hook["name"].format_map(prompt_mapping),
                        "args": { k.format_map(prompt_mapping): v.format_map(prompt_mapping) for k, v in hook["args"].items() }
                    }
                    hooks.append(hook)
            prompt._hooks = hooks
        if prompt._saves:
            prompt._saves = { key.format_map(prompt_mapping): to.format_map(prompt_mapping) for key, to in prompt._saves.items() }
        return prompt


    @property
    def id(self):
        return self._id.hex

    @property
    def params(self):
        return self._params

    @property
    def schema(self):
        return self._schema
    
    @property
    def hooks(self):
        return self._hooks
    
    @property
    def tools(self):
        return self._tools
    
    @property
    def validators(self):
        return self._validators

    @property
    def saves(self):
        return self._saves

    @property
    def is_tagged(self) -> bool:
        return self._tag
    
    @property
    def tag(self) -> Tag | None:
        return self._tag