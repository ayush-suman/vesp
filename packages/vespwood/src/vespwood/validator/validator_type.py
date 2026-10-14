from dataclasses import dataclass

from vespwood.types.params import Params
from vespwood_generator.blocks.block import Block
from .merge_strategy import MergeStrategy, discard_all, discard_invalid

@dataclass(kw_only=True)
class ValidatorType:
    content: Block | list[Block]
    params: Params | None = None
    merge_strategy: MergeStrategy


class ValidatorTypeOptions:
    DISCARD_ALL = ValidatorType(
        content = "",
        params = ["errors"],
        merge_strategy = discard_all
    )

    DISCARD_INVALID = ValidatorType(
        content = "",
        params = ["errors"],
        merge_strategy = discard_invalid
    )