from vespwood_generator import (
    Structured,
    Message,
    Generator, 
    Schema, 
    Tool
)
from jsf import JSF


class FakeResponseGenerator(Generator):
    async def __prompt__(self, messages: list[Message], schema: Schema | None = None, tools: list[Tool] | None = None) -> Message: 
        if schema:
            jsf = JSF(schema.schema)
            response = jsf.generate()
            return Message(Structured(response))
        else: 
            return Message("Skip")