import json
import os
from typing import Any

from openai import NOT_GIVEN, AsyncOpenAI, RateLimitError as OpenAIRateLimitError

from vespwood_generator import (
    message_converter, 
    Prompt, 
    Message,
    Response,
    Structured,
    ToolCall, 
    Generator, 
    Schema, 
    Tool, 
    RateLimitError, 
    MaxTokenLimitError, 
    StopGeneration
)



@message_converter
def _openai_chat_completion_msg_converter(message: Message) -> list[dict[str, Any]]:
    msgs = []
    
    for block in message.content:
        # TODO: Handle different types of blocks
        if isinstance(block, str):
            msgs.append({
                "role": message.role,
                "content": block
            })
        elif isinstance(block, dict):
            msgs.append({
                "role": message.role,
                "content": json.dumps(block)
            })
        elif isinstance(block, ToolCall):
            msgs.append({
                "role": message.role,
                "tool_calls": {
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.arguments)
                    }
                }
            })
            if block.result:
                msgs.append({
                    "role": "tool",
                    "tool_call_id": block.id,
                    "content": json.dumps(block.result)
                })
    return [*msgs]


class OpenAIChatCompletionGenerator(Generator):
    

    def __init__(self,
        api_key: str = os.getenv("OPENAI_API_KEY"), 
        model: str | dict[str, str] = "gpt-5.1",
        timeout: int = 300,
        *args,
        **kwds
    ):
        self.model_name = model
        self._model: AsyncOpenAI = AsyncOpenAI(api_key=api_key, timeout=timeout)
        

    async def __prompt__(self, messages: list[Prompt], schema: Schema | None = None, tools: list[Tool] | None = None) -> Response: 
        prompts = _openai_chat_completion_msg_converter(messages)

        response_format = NOT_GIVEN
        if schema:
            response_format = {
                "type": "json_schema", 
                "json_schema": {
                    "name": schema.name,
                    "schema": schema.schema,
                    "strict": True
                    }
                }

        tools_schema = NOT_GIVEN
        if tools:
            tools_schema = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema,
                "strict": True
            }
        } for tool in tools]

        try:
            response = await self._model.chat.completions.create(
                model=self.model_name, 
                messages=prompts, 
                response_format=response_format,
                tools=tools_schema,
            )

            # Refusal
            if response.choices[0].message.refusal:
                raise StopGeneration(response.choices[0].message.refusal)

            # Tool Call
            if response.choices[0].finish_reason == "tool_calls":
                blocks = [ToolCall(id=tool.id, name=tool.function.name, arguments=json.loads(tool.function.arguments)) for tool in response.choices[0].message.tool_calls]
                if text := response.choices[0].message.content:
                    blocks = [text, *blocks]
                return Response(blocks)
                
            # Unfinished Response
            elif response.choices[0].finish_reason == "length":
                raise MaxTokenLimitError(response.choices[0].message.content)
            
            # Structured Response
            if schema:
                return Response(Structured(response.choices[0].message.content))
            
            # Content
            return Response(response.choices[0].message.content)
        
        except OpenAIRateLimitError as e:
            raise RateLimitError()