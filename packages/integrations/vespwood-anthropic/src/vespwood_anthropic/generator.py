
import json
import os
from typing import Any
from anthropic import AsyncAnthropic, RateLimitError as AnthropicRateLimitError, omit
from vespwood_generator import (
    ToolCall,
    message_converter, 
    Message, 
    Response,
    Generator, 
    Schema, 
    Tool,
    RateLimitError, 
    MaxTokenLimitError, 
    StopGeneration
)
from vespwood_generator.blocks.structured import Structured


@message_converter
def _anthropic_messages_msg_converter(prompt: Message) -> list[dict[str, Any]]:
    msgs = []
    content = []
    for block in prompt:
        if isinstance(block, str):
            content.append({"type": "text", "text": block})
        elif isinstance(block, dict):
            content.append({"type": "text", "text": json.dumps(block)})
        elif isinstance(block, ToolCall):
            content.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.arguments})
        
    msgs.append({
        "role": "user" if prompt._role != "assistant" else "assistant",
        "content": content
    })

    if any(isinstance(block, ToolCall) for block in prompt.content):
        toolcalls: list[ToolCall] = list(filter(lambda b: isinstance(b, ToolCall), prompt.content))
        content = []
        for tool in toolcalls:
            content.append({
                "type": "tool_result",
                "tool_use_id": tool.id,
                "content": json.dumps(tool.result)
            })
        msgs.append({
            "role": "user",
            "content": content
        })
    return msgs


class AnthropicMessagesGenerator(Generator):
    __slots__ = ("model_name", "_model")

    def __init__(self, 
                api_key: str = os.getenv("ANTHROPIC_API_KEY"),
                model: str | dict[str, str] = "claude-sonnet-4-5-20250929",
                max_tokens: int = 4096,
                timeout: int = 300,
                *args,
                **kwargs):
        self.model_name = model
        self._model = AsyncAnthropic(api_key=api_key, timeout=timeout)
    

    async def __prompt__(self, messages: list[Message], schema: Schema | None = None, tools: list[Tool] | None = None):
        prompts = _anthropic_messages_msg_converter(messages)
        
        output_config = omit
        if schema:
            output_config = {
                "format": {
                    "type": "json_schema", 
                    "schema": schema.schema,
                }
            }


        anthropic_tools = omit
        if tools:
            anthropic_tools = []
            for tool in tools:
                _anthropic_tool = {
                    "name": tool.name,
                    "input_schema": tool.schema
                    }
                if tool.description:
                    _anthropic_tool.update({
                        "description": tool.description
                    })
                anthropic_tools.append(_anthropic_tool)
                
        
        try:
            message = await self._model.messages.create(
                max_tokens=128000,
                model=self.model_name,
                messages=prompts,
                tools=anthropic_tools,
                output_config=output_config,
            )

            # Refusal
            if message.stop_reason == "refusal":
                raise StopGeneration(f"Anthropic model {self.model_name} refused to respond to this request")
            
            # Structured
            if schema:
                try:
                    return Response(Structured(json.loads("".join([block.text for block in message.content if block.type=="text"]))))
                except Exception as e:
                    print("\n\n**Failed to parse response as JSON**\nblock: \n\n", block.text)
                    raise e
                
            response = Response([])
            for block in message.content:
                if block.type == "text":
                    response.append(block.text)
                elif block.type == "tool_use":
                    response.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
                elif block.type == "thinking":
                    # TODO:
                    ...
                    # response.append(ThinkingBlock(id=block.signature, content=block.thinking))
                elif block.type == "redacted_thinking":
                    # TODO:
                    ...

            # Unfinished Response
            if message.stop_reason == "max_tokens" or message.stop_reason == "model_context_window_exceeded":
                print("Output token limit exceeded. Continuing generation...")
                raise MaxTokenLimitError(response.content)

            return response
        
        except AnthropicRateLimitError:
            raise RateLimitError()
