from vespwood.message import Message
from vespwood._utils import get_key_index

type MessageGroup = Message | list[MessageGroup]

class TaggedMessages(dict[str, MessageGroup]):
    def __getitem__(self, key: str):
        if "#" in key:
            key, index = get_key_index(key)
            base = self.__getitem__(key)
            if base:
                if index >= len(base):
                    return None
                return base.__getitem__(index)
        if key in self: 
            return super().__getitem__(key)

    def __setitem__(self, key: str, value: MessageGroup):
        if "#" in key:
            key, index = get_key_index(key)
            base = self.__getitem__(key)
            if base:
                assert isinstance(base, list)
                if index >= len(base): 
                    base.extend([None] * (index - len(base) + 1))
                base.__setitem__(index, value)
            else:
                self.__setitem__(key, [*[None] * (index - 1), value])
        else:
            super().__setitem__(key, value)

