from vespwood_generator.blocks.block import Block
from vespwood_generator.message import Message

from .merge_strategy import merge_strategy


@merge_strategy
def discard_all(_: list[Block], merged_message: Message):
    return Message(merged_message.role, [])