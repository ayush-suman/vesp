from typing import Any
from vespwood_generator.blocks import Block, Structured, ToolCall, Image, File
from vespwood_generator.types import Role


class Message:
    __slots__ = "_role", "_content"

    def __init__(self, 
        role: Role, 
        content: Block | list[Block] | None = None
    ):
        self._role = role
        self._content: list[Block] = []
        if isinstance(content, (str, Structured, ToolCall, Image, File)):
            self._content = [content]
        elif isinstance(content, list):
            self._content = content
             
    @property
    def role(self) -> Role:
        return self._role

    @property
    def content(self) -> list[Block]:
        return self._content

    def __iter__(self) -> list[Block]:
        return iter(self._content or [])
    
    def append(self, block: Block):
        if self._content is None: self._content = []
        self._content.append(block)
    
    def extend(self, content: list[Block]):
        if self._content is None: self._content = []
        for block in content: self.append(block)

    def update_content(self, content: Block | list[Block] | None):
        if content is None:
            self._content = None
        elif isinstance(content, (str, Structured, ToolCall, Image, File)):
            self._content = [content]
        elif isinstance(content, list):
            self._content = content

    def __getitem__(self, key):
        print(f"Message.__getitem__ called with key: {key}")
        for block in self.content:
            print("block of type:", type(block))
            if isinstance(block, Structured): 
                print(f"Checking block: {block}")
                return block[key]
            else: 
                return None

    def __setitem__(self, *_):
        raise NotImplementedError("Setting values to Message is not supported")
    
    def update(self, _):
        raise NotImplementedError("Setting values to Message is not supported")
    
    def get(self, key: str, default: Any = None):
        return self.__getitem__(key) or default

    def indexed(self, idx: int) -> "Message":
        self._id = self.id + f"#{idx}"
        return self
        
    @property
    def json(self):
        data = { "role": self.role, "content": self.content }
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