from abc import abstractmethod, ABCMeta
import asyncio
from typing import Any
from vespwood_generator.schematic import Schema, Tool
from vespwood_generator.errors import MaxTokenLimitError, RateLimitError, ValidationError
from vespwood_generator.message import Message
from vespwood_generator.validator import Validator


class GeneratorClass(ABCMeta):
    def __call__(self, *args, **kwds):
        return super().__call__(*args, **kwds)


class Generator(metaclass=GeneratorClass):
    def __init__(self, *args, **kwargs): 
        ...
        
        
    @abstractmethod
    async def __prompt__(self, 
        messages: list[Message], 
        schema: Schema | None = None,
        tools: list[Tool] | None = None
    ) -> Message: ...


    async def get_response(self, messages: list[Message], args: dict[str, Any], schema: Schema | None, tools: list[Tool] | None, validators: list[Validator] | None, continue_on_max_token: bool = True, retry_on_rate_limit: bool = True, retry_with_delay: int = 0) -> Message:
        response = None
        try:
            response = await self.__prompt__(messages, schema, tools)
            if validators:
                for v in validators: 
                    v = v.suppliment(**args)
                    await v(messages, response)
            return response
        except ValidationError as e:
            messages.append(response)
            messages.append(Message(role="system", content=e.content))
            return await self.get_response(
                messages=messages,
                args=args,
                schema=schema,
                tools=tools,
                validators=validators,
                continue_on_max_token=continue_on_max_token,
                retry_on_rate_limit=retry_on_rate_limit,
                retry_with_delay=retry_with_delay
            )
        except MaxTokenLimitError as e:
            print("Output token limit exceeded.")
            if continue_on_max_token:
                print("Continuing generation...")
                response = Message(role="assistant", content=e.generated_content)
                messages.append(response)
                remaining_response: Message = await self.get_response(
                    messages=messages,
                    args=args,
                    tools=tools,
                    validators=validators,
                    continue_on_max_token=continue_on_max_token,
                    retry_on_rate_limit=retry_on_rate_limit,
                    retry_with_delay=retry_with_delay
                )
                response.extend(remaining_response.content)
                return response
            raise e
        except RateLimitError as e:
            if retry_on_rate_limit:
                await asyncio.sleep(retry_with_delay)
                return await self.get_response(
                    messages=messages,
                    args=args,
                    tools=tools,
                    schema=schema,
                    validators=validators,
                    continue_on_max_token=continue_on_max_token,
                    retry_on_rate_limit=retry_on_rate_limit,
                    retry_with_delay=retry_with_delay
                )