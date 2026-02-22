import json
import os
from typing import Any

from openai import NOT_GIVEN, AsyncOpenAI, RateLimitError as OpenAIRateLimitError

from vespwood import (
    message_converter, 
    Prompt, 
    Response,
    Structured,
    ToolCall, 
    Generator, 
    Schema, 
    Tool, 
    Role, 
    RateLimitError, 
    MaxTokenLimitError, 
    StopGeneration
)



@message_converter
def _openai_chat_completion_msg_converter(prompt: Prompt) -> list[dict[str, Any]]:
    msg = {
        "role": prompt.role
    }
    tool_call_results = []

    for block in prompt.content:
        # TODO: Handle different types of blocks
        if isinstance(block, str):
            msg.update({
                "content": block
            })
        elif isinstance(block, dict):
            msg.update({
                "content": json.dumps(block)
            })

    if any(isinstance(block, ToolCall) for block in prompt.content):
        calls: list[ToolCall] = list(filter(lambda b: isinstance(b, ToolCall), prompt.content))
        tool_calls = []
        for tool in calls:
            tool_calls.append({
                "id": tool.id,
                "type": "function",
                "function": {
                    "name": tool.name,
                    "arguments": json.dumps(tool.arguments)
                }
            })
            tool_call_results.append({
                "role": "tool",
                "tool_call_id": tool.id,
                "content": json.dumps(tool.result)
            })
        msg.update({
            "tool_calls": tool_calls
        })
    return [msg, *tool_call_results]


class OpenAIChatCompletionGenerator(Generator):
    @staticmethod
    def response_to_message(role: Role, response: str):
        return [] if response == "" else [{"role": role, "content": response}]
    

    def __init__(self,
        api_key: str = os.getenv("OPENAI_API_KEY"), 
        model: str | dict[str, str] = "gpt-5.1",
        timeout: int = 300,
        *args,
        **kwds
    ):
        self.model_name = model
        self._model: AsyncOpenAI = AsyncOpenAI(api_key=api_key, timeout=timeout)
        

    async def __prompt__(self, messages: list[Prompt], schema: Schema | None = None, tools: list[Tool] | None = None, assistant_response: str = "", validator_response: str = "", **kwargs) -> Response:
        prompts = _openai_chat_completion_msg_converter(messages)
        assistant_message = OpenAIChatCompletionGenerator.response_to_message("assistant", assistant_response)
        validator_message = OpenAIChatCompletionGenerator.response_to_message("system", validator_response)
        
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
                messages=prompts+validator_message+assistant_message, 
                response_format=response_format,
                tools=tools_schema,
            )
            content = response.choices[0].message.content or ""
            print("Content", content)
            assistant_response = assistant_response + content 

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
                raise MaxTokenLimitError(assistant_response)
            
            # Structured Response
            if schema:
                print("Assistant Response", assistant_response)
                return Response(Structured(assistant_response))
            
            # Content
            return Response(assistant_response)
        
        except OpenAIRateLimitError as e:
            raise RateLimitError()