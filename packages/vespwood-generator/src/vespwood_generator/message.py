from __future__ import annotations
from enum import Enum
from typing import Any, Self
import uuid
from vespwood_generator.blocks import Block, ToolCall, Image, File
from vespwood_generator.structured import Structured
from vespwood_generator.types import Role


class AwaitedType(Enum):
    REQUIRE_TOOL_RESULT = 1
    REQUIRE_CONTENT = 2

    
class Message:
    __slots__ = "_role", "_content"

    def __init__(self, 
        role: Role, 
        content: Block | list[Block] | Structured | None = None
    ):
        self._role = role
        self._content: list[Block] | Structured = []
        if isinstance(content, (str, ToolCall, Image, File)):
            self._content = [content]
        elif isinstance(content, (Structured, list)):
            self._content = content
             
    @property
    def role(self) -> Role:
        return self._role

    @property
    def content(self) -> list[Block] | Structured | None:
        return self._content
    
    def append(self, block: Block):
        if self._content is None: self._content = []
        if isinstance(self._content, Structured): 
            raise TypeError("Can not add blocks to message with Structured content")
        self._content.append(block)
    
    def extend(self, content: list[Block]):
        if self._content is None: self._content = []
        if isinstance(self._content, Structured): 
            raise TypeError("Can not add blocks to message with Structured content")
        for block in content: self.append(block)

    def copy(self) -> Message:
        new_message = Message(self._role)
        new_message._content = self._content.copy()
        return new_message

    def indexed(self, idx: int) -> Self:
        self = self.copy()
        self._id = uuid.uuid5(self._id, str(idx))
        return self
        
    @property
    def json(self):
        data = { "role": self.role, "content": self.content }
        return data

    # @property
    # def structured(self) -> Structured:
    #     for block in self:
    #         if isinstance(block, Structured):
    #             return block
    #     raise ValueError("This response does not have any structured response")

    def __str__(self) -> str:
        data = self.json
        import json
        return json.dumps(data, indent=2)

    def __repr__(self) -> str:
        data = { "role": self._role, "content": list(map(lambda block: block.json if isinstance(block, ToolCall) else block, self.content)) }
        import json
        return json.dumps(data, indent=2)

    @property
    def is_awaited(self) -> bool:
        if self._content is None or len(self._content) == 0:
            print("Content is None or empty")
            return True
        if any([(isinstance(block, ToolCall) and block.result is None) for block in self._content]):
            print("Tool Call Result pending")
            return True
        return False

    @property
    def awaited_type(self) -> AwaitedType | None:
        if self._content is None or len(self._content) == 0:
            return AwaitedType.REQUIRE_CONTENT
        if any([(isinstance(block, ToolCall) and block.result is None) for block in self._content]):
            return AwaitedType.REQUIRE_TOOL_RESULT
        return None