from typing import Any

from vespwood.blocks import Block, Structured
from vespwood.types.role import Role


class Message:
    __slots__ = "_role", "_content", "_structured"

    def __init__(self, 
        role: Role, 
        content: Block | list[Block] | None = None
    ):
        self._role = role
        self._content: list[Block] = []
        self._structured: dict = {}
        if isinstance(content, list):
            self._content = content
        else:
            self._content = [content]

        for block in self.content:
            if isinstance(block, Structured):
                self._structured.update(block)    
    
    @property
    def role(self) -> Role:
        return self._role

    @property
    def content(self) -> list[Block]:
        return self._content

    def __iter__(self) -> list[Block]:
        return iter(self._content)
    
    def append(self, block: Block):
        self._content.append(block)
        if isinstance(block, Structured):
            self._structured.update(block)

    def __getitem__(self, key):
        if key in self._structured: return self._structured.__getitem__(key)

    def __setitem__(self, *_):
        raise NotImplementedError("Setting values to Message is not supported")
    
    def update(self, _):
        raise NotImplementedError("Setting values to Message is not supported")
    
    def get(self, key: str, default: Any = None):
        return self.__getitem__(key) or default