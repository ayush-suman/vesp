from vespwood_generator.blocks import Block


class MaxTokenLimitError(Exception):
    def __init__(self, generated_content: list[Block]):
        self.generated_content: list[Block] = generated_content
        super().__init__(generated_content)