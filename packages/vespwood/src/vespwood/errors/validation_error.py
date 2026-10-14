from typing import Any

from vespwood_generator import Block


class ValidationError(Exception):
    def __init__(self, invalid_blocks: list[Block], **args):
        self._invalid_blocks = invalid_blocks
        self._format_args = args
        super().__init__("Validator failed for blocks", self._invalid_blocks)

    @property
    def invalid_blocks(self) -> list[Block]:
        return self._invalid_blocks

    @property
    def format_args(self) -> dict[str, Any]:
        return self._format_args
