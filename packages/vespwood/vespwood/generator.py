from abc import abstractmethod, ABCMeta
import asyncio
from vespwood.schematic import Schema, Tool
from vespwood.errors import MaxTokenLimitError, RateLimitError, ValidationError
from vespwood.message import Prompt, Response
from vespwood.validator import Validator


class GeneratorClass(ABCMeta):
    def __call__(self, *args, **kwds):
        return super().__call__(*args, **kwds)


class Generator(metaclass=GeneratorClass):
    @abstractmethod
    async def __prompt__(self, 
        messages: list[Prompt], 
        schema: Schema | None = None,
        tools: list[Tool] | None = None, 
        assistant_response: str = "", 
        validator_response: str = "", 
        **kwargs):
        ...

    async def get_response(self, messages: list[Prompt], schema: Schema | None, tools: list[Tool] | None, validators: list[Validator] | None, continue_on_max_token: bool = True, retry_on_rate_limit: bool = True, retry_with_delay: int = 0, **kwargs) -> Response:
        try:
            response = await self.__prompt__(messages, schema, tools, **kwargs)
            if validators:
                for v in validators: v.validate(response, messages, kwargs)
            return response
        except ValidationError as e:
            return await self.get_response(
                messages=messages,
                schema=schema,
                tools=tools,
                validators=validators,
                validator_response=e.validator_response,
                **kwargs
            )
        except MaxTokenLimitError as e:
            print("Output token limit exceeded.")
            if continue_on_max_token:
                print("Continuing generation...")
                return await self.get_response(
                    messages=messages,
                    tools=tools,
                    validators=validators,
                    assistant_response=e.assistant_response,
                    **kwargs
                )
            raise e
        except RateLimitError as e:
            if retry_on_rate_limit:
                await asyncio.sleep(retry_with_delay)
                return await self.get_response(
                    messages=messages,
                    tools=tools,
                    validators=validators,
                    **kwargs
                )