from vespwood_generator.blocks.block import Block
from vespwood_generator.message import Message

from .merge_strategy import merge_strategy


@merge_strategy
def discard_invalid(invalid_blocks: list[Block], merged_message: Message):
    return Message(
        merged_message.role, 
        list(
            filter(
                lambda block: block not in invalid_blocks, merged_message.content
            )
        )
    )