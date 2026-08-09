
from typing import Any
from enum import Enum
import uuid
from vespwood_generator import (
    Message,
    File, Image, ToolCall,
    Tag, Role,
    Block
)

from vespwood.types import (
    Params, HooksList, SchemaInfo, ToolsList, ValidatorsList, Saves
)

class AwaitedType(Enum):
    REQUIRE_TOOL_RESULT = 1
    REQUIRE_CONTENT = 2

class Prompt(Message):
    __slots__ = "_tag", "_params", "_schema", "_tools", "_hooks", "_validators", "_saves", "_json"

    def __init__(self, 
                id: str,
                *,
                role: Role, 
                content: Block | list[Block] | None = None, 
                params: Params | None = None, 
                schema: SchemaInfo | None = None, 
                tools: ToolsList | None = None,
                hooks: HooksList | None = None,
                validators: ValidatorsList | None = None,
                saves: Saves | None = None):
        self._id: str = id
        self._params: Params | None = params
        self._schema: SchemaInfo | None = schema
        self._tools: ToolsList | None = tools
        self._hooks: HooksList | None = hooks
        self._validators: ValidatorsList | None = validators
        self._saves: Saves | None = saves
        self._tag: Tag = None
        super().__init__(role, content)


    @classmethod
    def load_from_dict(cls, data: dict):
        def convert(content: str | dict) -> str | dict | Image | File | ToolCall:
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
        prompt = cls(
            uuid.uuid4().hex,
            role=role,
            content=content, 
            params=params, 
            schema=schema, 
            tools=tools, 
            hooks=hooks, 
            validators=validators, 
            saves=saves
        ) @ data.get("tag")

        return prompt

    @property
    def is_tagged(self) -> bool:
        return self._tag
    
    @property
    def tag(self) -> Tag:
        return self._tag

    def __matmul__(self, other: str | Tag | None) -> "Message":
        if other is None:
            return self
        if self.is_tagged:
            raise ValueError("This response is already tagged with", self._tag, "as tag")
        self._tag = Tag(other) if isinstance(other, str) else other
        return self
    
    @property
    def is_awaited(self) -> bool:
        if self._content is None or len(self._content) == 0:
            return True
        if any([(isinstance(block, ToolCall) and block.result is None) for block in self._content]):
            return True
        return False
    

    def copy(self):
        prompt = Prompt(
            self._id,
            role=self._role, 
            content=self._content.copy() if self._content else None, 
            params=self._params.copy() if self._params else None,
            schema=self._schema.copy() if isinstance(self._schema, dict) else self._schema,
            tools=self._tools.copy() if self._tools else None,
            hooks=self._hooks.copy() if self._hooks else None,
            validators=self._validators.copy() if self._validators else None,
            saves=self._saves.copy() if self._saves else None
        )
        if self.is_tagged: 
            prompt @= self.tag
        return prompt
    
    def __copy__(self):
        return self.copy()


    def format_map(self, prompt_mapping) -> "Prompt":
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
        return self._id

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
    def saved_args(self) -> dict[str, Any]:
        if self._saves and self._schema and self._content:
            return { to: self.get(key) for key, to in self._saves.items() }
        return {}

    @property
    def awaited_type(self) -> AwaitedType | None:
        if self._content is None or len(self._content) == 0:
            return AwaitedType.REQUIRE_CONTENT
        if any([(isinstance(block, ToolCall) and block.result is None) for block in self._content]):
            return AwaitedType.REQUIRE_TOOL_RESULT
        return None
