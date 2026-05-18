from google.genai import Client
from google.genai.types import Content, Part, FunctionCall, FunctionResponse, GenerateContentConfig, Tool as GoogleTool, FunctionDeclaration
from typing import overload
from vespwood_generator import Generator, message_converter, Message, Structured, ToolCall, Schema, Tool, Response
import json


@message_converter
def _google_genai_message_converter(prompt: Message):
    parts = []
    for block in prompt.content:
        if isinstance(block, str):
            parts.append(Part(text=block))
        elif isinstance(block, Structured):
            parts.append(Part(text=json.dumps(block)))
        elif isinstance(block, ToolCall):
            parts.append(Part(function_call=FunctionCall(id=block.id, name=block.name, args=block.arguments)))

    contents = [Content(parts=parts, role="user" if prompt.role != "assistant" else "model")]

    if any(isinstance(block, ToolCall) for block in prompt.content):
        toolcalls: list[ToolCall] = list(filter(lambda b: isinstance(b, ToolCall), prompt.content))
        for block in toolcalls:
            contents.append(
                Content(
                    parts=FunctionResponse(id=block.id, name=block.name, response=block.result if isinstance(block, dict) else { "result": block.result }), 
                    role="function"
                )
            )
    return contents


class GoogleGenAIGenerator(Generator):
    @overload
    def __init__(self, *, api_key: str, model: str = "gemini-2.0-flash", **kwargs): ...
    @overload
    def __init__(self, *, project: str, location: str, model: str = "gemini-2.0-flash", **kwargs): ...
    def __init__(self, *, api_key: str | None = None, project: str | None = None, location: str | None, model: str = "gemini-2.0-flash", **kwargs):
        if api_key:
            self.client = Client(api_key=api_key).aio
        else:
            self.client = Client(vertexai=True, project=project, location=location)
        self.model_name = model


    async def __prompt__(
        self, 
        messages: list[Message], 
        schema: Schema | None = None, 
        tools: list[Tool] | None = None
    ):
        contents = _google_genai_message_converter(messages)
        
        google_tools = None
        if tools:
            function_declarations = []
            for tool in tools:
                function_declarations.append(FunctionDeclaration(name=tool.name, description=tool.description, parameters_json_schema=tool.schema))
            google_tools = [GoogleTool(function_declarations=function_declarations)]


        output = await self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=GenerateContentConfig(
                tools=google_tools, 
                response_mime_type="application/json" if schema else None,
                response_json_schema=schema.schema if schema else None
            )
        )

        if schema:
            return Response(Structured(output.text))
        
        response = Response([])
        content = output.candidates[0].content
        for part in content.parts:
            if part.text:
                response.append(part.text)
            elif f:=part.function_call:
                response.append(ToolCall(id=f.id, name=f.name, arguments=f.args))
            
        return response



