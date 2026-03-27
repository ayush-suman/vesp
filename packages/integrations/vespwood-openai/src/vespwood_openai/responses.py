import json
import os

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
def _openai_response_msg_converter(prompt: Prompt):
    msgs = []
    content = []
    for block in prompt:
        t = "output_text" if prompt.role == "assistant" else "input_text"
        if isinstance(block, str):
            content.append({"type": t, "text": block})
        elif isinstance(block, dict):
            content.append({"type": t, "text": json.dumps(block)})
        elif isinstance(block, ToolCall):
            if content:
                msgs.append({"role": prompt.role, "content": content})
                content = []
            msgs.append({"call_id": block.id, "type": "function_call", "name": block.name, "arguments": json.dumps(block.arguments)})
        
    msgs.append({
        "role": "developer" if prompt.role == "system" else prompt.role,
        "content": content
    })

    if any(isinstance(block, ToolCall) for block in prompt.content):
        toolcalls: list[ToolCall] = list(filter(lambda b: isinstance(b, ToolCall), prompt.content))
        content = []
        for tool in toolcalls:
            msgs.append({
                "type": "function_call_output",
                "call_id": tool.id,
                "output": json.dumps(tool.result)
            })
    return msgs


class OpenAIResponsesGenerator(Generator):
    def __init__(self, 
        api_key: str = os.getenv("OPENAI_API_KEY"), 
        model: str | dict[str, str] = "gpt-5.1",
        timeout: int = 300,
        *args,
        **kwds
    ):
        self.model_name = model
        self._model = AsyncOpenAI(api_key=api_key, timeout=timeout)

    @classmethod
    def response_to_message(cls, role: Role, response: str):
        return [] if response == "" else [{"role": role, "content": response}]


    async def __prompt__(self, messages: list[Prompt], schema: Schema | None = None, tools: list[Tool] | None = None, assistant_response: str = "", validator_response: str = "", **kwargs) -> Response:
        prompts = _openai_response_msg_converter(messages)
        assistant_message = OpenAIResponsesGenerator.response_to_message("assistant", assistant_response)
        validator_message = OpenAIResponsesGenerator.response_to_message("user", validator_response)
        
        output_format = NOT_GIVEN
        if schema:
            output_format = {
                "type": "json_schema", 
                "name": schema.name,
                "schema": schema.schema,
            }

        openai_tools = NOT_GIVEN
        if tools:
            openai_tools = [{
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema
                } for tool in tools
            ]
        
        try:
            response = await self._model.responses.create(
                model=self.model_name,
                input=prompts + validator_message + assistant_message,
                tools=openai_tools,
                text={"format": output_format},
                store=False
            )
            print("Respone Output", response.output)
            assistant_response = assistant_response + response.output_text
            
            # Unfinished Response
            # if response.stop_reason == "max_tokens" or response.stop_reason == "model_context_window_exceeded":
            #     print("Output token limit exceeded. Continuing generation...")
            #     raise MaxTokenLimitError(assistant_response)
            
            # Tool Call
            r = Response()
            for message in response.output:
                if message.type == "message":
                    if schema:
                        text = message.model_dump()["content"][0]["text"]
                        r.append(Structured(text))
                    else:
                        for block in message.content:
                            if block.type == "output_text":
                                r.append(block.text)
                elif message.type == "function_call":
                    r.append(ToolCall(id=message.id, name= message.name, arguments=json.loads(message.arguments)))
                elif message.type == "reasoning":
                    # TODO:
                    ...
                # elif block.type == "thinking":
                #     response.append(ThinkingBlock(id=block.signature, content=block.thinking))
                # elif block.type == "redacted_thinking":

            return r
        
        except OpenAIRateLimitError:
            raise RateLimitError()