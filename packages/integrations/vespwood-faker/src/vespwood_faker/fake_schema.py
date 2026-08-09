from vespwood_generator import (
    Prompt,
    Structured,
    Response,
    Generator, 
    Schema, 
    Tool
)
from jsf import JSF


class FakeResponseGenerator(Generator):
    async def __prompt__(self, messages: list[Prompt], schema: Schema | None = None, tools: list[Tool] | None = None) -> Response: 
        if schema:
            jsf = JSF(schema.schema)
            response = jsf.generate()
            return Response(Structured(response))
        else: 
            return Response("Skip")