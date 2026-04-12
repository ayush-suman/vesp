from vespwood_generator import (
    Message,
    Response,
    Generator, 
    Schema, 
    Tool
)
from jsf import JSF


class FakeSchemaGenerator(Generator):
    async def __prompt__(self, messages: list[Message], schema: Schema | None = None, tools: list[Tool] | None = None) -> Response: 
        if schema:
            jsf = JSF(schema.schema)
            response = jsf.generate()
            return Response(response)
        else: 
            return Response("Skip")