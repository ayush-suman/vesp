from vespwood.tag import Tag
from vespwood.blocks import Block
from .message import Message


class Response(Message):
    __slots__ = "_tag",  "_messages"

    def __init__(self, content: Block | list[Block] | None = None):
        self._tag: Tag | None = None
        super().__init__("assistant", content)

    @property
    def is_tagged(self) -> bool:
        return self._tag
    
    @property
    def tag(self) -> Tag:
        return self._tag
    
    @property
    def index(self) -> int | None:
        return self.tag.index


    def __matmul__(self, other: str):
        if self.is_tagged:
            raise ValueError("This response is already tagged with", self._tag, "as tag")
        self._tag = Tag(other)
        return self
    