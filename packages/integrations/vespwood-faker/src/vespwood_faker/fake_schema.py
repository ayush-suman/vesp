from vespwood_generator import (
    Message,
    Structured,
    Response,
    Generator, 
    Schema, 
    Tool
)
from jsf import JSF


class FakeResponseGenerator(Generator):
    async def __prompt__(self, messages: list[Message], schema: Schema | None = None, tools: list[Tool] | None = None) -> Response: 
        if schema:
            jsf = JSF(schema.schema)
            response = jsf.generate()
            return Response(Structured(response))
        else: 
            return Response("Skip")