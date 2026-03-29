from vespwood_generator.blocks import Block

class ValidationError(Exception):
    def __init__(self, *content: list[Block]):
        self.content: list[Block] = list(content)
        super().__init__(content)