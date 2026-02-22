
from vespwood.types.params import Params
from vespwood.types.hooks_list import HooksList
from vespwood.types.role import Role
from vespwood.types.saves import Saves
from vespwood.types.schema_info import SchemaInfo
from vespwood.types.tools_list import ToolsList
from vespwood.types.validators_list import ValidatorsList
from vespwood.tag import Tag
from vespwood.blocks import Block, File, Image, ToolCall
from .message import Message

class Prompt(Message):
    __slots__ = "_params", "_schema", "_tools", "_hooks", "_validators", "_saves", "_json", "_tag"

    @property
    def is_tagged(self) -> bool:
        return self._tag
    

    @property
    def tag(self) -> Tag:
        return self._tag


    def __matmul__(self, other: str) -> "Prompt":
        prompt = self.copy()
        prompt._tag = Tag(other)
        return prompt


    @classmethod
    def AWAITING_RESPONSE(cls):
        self = super().__new__(cls)
        self.__init__("assistant")
        return self
    

    def __init__(self, 
                role: Role, 
                content: Block | list[Block] | None = None,
                params: Params | None = None, 
                schema: SchemaInfo | None = None, 
                tools: ToolsList | None = None,
                hooks: HooksList | None = None,
                validators: ValidatorsList | None = None,
                saves: Saves | None = None):
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
        # if isinstance(saves, list):
        #     map(, saves)
        prompt: Prompt = cls(content=content, role=role, params=params, schema=schema, tools=tools, hooks=hooks, validators=validators, saves=saves) 

        tag = data.get("tag")
        if role == "assistant" and tag is None:
            raise ValueError("Assistant prompts should have tag fields")
        if tag:
            prompt @= tag
        return prompt
    
    
    @property
    def response_awaited(self) -> bool:
        null_response = self._role == "assistant" and (not self._content  or len(self._content) == 0)
        return null_response
    

    def copy(self):
        prompt = Prompt(
            role=self._role, 
            content=self._content.copy() if self._content else None, 
            params=self._params.copy() if self._params else None,
            tools=self._tools.copy() if self._tools else None,
            schema=self._schema.copy() if isinstance(self._schema, dict) else self._schema,
            hooks=self._hooks.copy() if self._hooks else None,
            saves=self._saves.copy() if self._saves else None)
        if self.is_tagged: 
            prompt @= self.tag
        return prompt
    
    def __copy__(self):
        return self.copy()


    def format(self, prompt_mapping) -> "Prompt":
        prompt = self.copy()
        if prompt._content: 
            content = []
            for block in prompt._content:
                if isinstance(block, str):
                    print(prompt_mapping.keys())
                    block = block.format_map(prompt_mapping)
                content.append(block)
            prompt._content = content
        return prompt


    def update_message(self, message: Message):
        if self.role != message.role:
            raise ValueError("Cannot add messsage with different role to prompt")
        self._content = message._content

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
    def json(self):
        data = { "role": self.role, "content": self.content }
        if self.is_tagged:
            data.update({ "tag": self.tag })
        return data

    def __str__(self) -> str:
        data = self.json
        import json
        return json.dumps(data, indent=2)


    def __repr__(self) -> str:
        data = { "role": self._role, "content": list(map(lambda block: block.json if isinstance(block, ToolCall) else block, self.content)) }
        if self.is_tagged:
            data.update({ "tag": self.tag })
        import json
        return json.dumps(data, indent=2)