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
    
    @property
    def json(self):
        data = { "role": self.role, "content": self.content }
        return data

    def __iter__(self) -> list[Block]:
        return iter(self._content)
    
    def append(self, block: Block):
        self._content.append(block)
    
    def extend(self, content: list[Block]):
        for block in content: self.append(block)

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