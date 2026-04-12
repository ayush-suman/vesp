from abc import abstractmethod, ABCMeta
import asyncio
from typing import Any
from vespwood_generator.schematic import Schema, Tool
from vespwood_generator.errors import MaxTokenLimitError, RateLimitError, ValidationError
from vespwood_generator.message import Response, Message
from vespwood_generator.validator import Validator


class GeneratorClass(ABCMeta):
    def __call__(self, *args, **kwds):
        return super().__call__(*args, **kwds)


class Generator(metaclass=GeneratorClass):
    @abstractmethod
    async def __prompt__(self, 
        messages: list[Message], 
        schema: Schema | None = None,
        tools: list[Tool] | None = None, 
        assistant_response: Message | None = None, 
        validator_response: Message | None = None, 
    ): ...


    async def get_response(self, messages: list[Message], format_keys: dict[str, Any], schema: Schema | None, tools: list[Tool] | None, validators: list[Validator] | None, continue_on_max_token: bool = True, retry_on_rate_limit: bool = True, retry_with_delay: int = 0, **kwargs) -> Response:
        response = None
        try:
            response = await self.__prompt__(messages, schema, tools, **kwargs)
            if validators:
                for v in validators: v.validate(messages, response, format_keys)
            return response
        except ValidationError as e:
            messages.append(response)
            messages.append(Message(role="system", content=e.content))
            return await self.get_response(
                messages=messages,
                format_keys=format_keys,
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
                remaining_response: Response = await self.get_response(
                    messages=messages,
                    format_keys=format_keys,
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
                    format_keys=format_keys,
                    tools=tools,
                    schema=schema,
                    validators=validators,
                    continue_on_max_token=continue_on_max_token,
                    retry_on_rate_limit=retry_on_rate_limit,
                    retry_with_delay=retry_with_delay
                )