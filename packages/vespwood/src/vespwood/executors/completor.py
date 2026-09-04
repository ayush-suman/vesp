from typing import Any
import uuid
import asyncio
from vespwood_generator.indexed_list import IndexedList
from vespwood.executors.executor import Executor
from vespwood_generator import (
    Generator,
    Schema,
    StopGeneration, Tool,
    Validator,
    AwaitedType
)
from vespwood.executors._prompt import _Prompt
from vespwood._utils import invoke_funcs
from vespwood.interceptor import Interceptor
from vespwood.hook import Hook
from vespwood.prompt_structure import MessageList, PromptStructure
from vespwood.errors import MissingParamError, MissingSchemaError, MissingToolError, MissingHookError, MissingValidatorError, MissingStructureError


class Completor(Executor):
    __slots__ = "_generator", "_prompt_structure", "_name", "_description", "_params", "_schemas", "_tools", "_hooks", "_validators", "_interceptors", "_output", "_delay_constant", "_max_requests", "_generation_queue", "_lock", "_continue_on_max_token", "_retry_on_rate_limit", "_retry_with_delay",

    def __init__(self,
                generator: Generator,
                *,
                schemas: list[Schema] = [],
                tools: list[Tool] = [],
                hooks: list[Hook] = [],
                validators: list[Validator] = [],
                interceptors: list[Interceptor] = [],
                structures: list[PromptStructure],
                delay_constant: int = 0,
                max_requests: int = 0,
                continue_on_max_token: bool = True,
                retry_on_rate_limit: bool = True,
                retry_with_delay: int = 0
            ):

        self._schemas = IndexedList(schemas, key=lambda s: s.name)
        self._tools = IndexedList(tools, key=lambda t: t.name)
        self._hooks = IndexedList(hooks, key=lambda h: h.name)
        self._validators = IndexedList(validators, key=lambda v: v.name)
        self._structures = IndexedList(structures, key=lambda s: s.name)
        
        self._generator: Generator = generator
        self._interceptors: list[Interceptor] = interceptors
        self._delay_constant: int = delay_constant
        self._max_requests: int = max_requests
        self._generation_queue: asyncio.Queue = asyncio.Queue(maxsize=max_requests or 0)
        self._lock = asyncio.Lock()

        self._continue_on_max_token = continue_on_max_token
        self._retry_on_rate_limit = retry_on_rate_limit,
        self._retry_with_delay = retry_with_delay


    def validate_for(self, prompt_structure: PromptStructure) -> None:
        schema_list = set(filter(lambda s: isinstance(s, str), prompt_structure.schemas or []))
        schema_names = set(map(lambda s: s.name, self._schemas))
        if diff := schema_list - schema_names:
            raise MissingSchemaError(*diff)

        tool_list = set(map(lambda t: t["name"] if isinstance(t, dict) else t, prompt_structure.tools or []))
        tool_names = set(map(lambda t: t.name, self._tools))
        if diff := tool_list - tool_names:
            raise MissingToolError(*diff)

        hook_list = set(prompt_structure.hooks or [])
        hook_names = set(map(lambda h: h.name, self._hooks))
        if diff := hook_list - hook_names:
            raise MissingHookError(*diff)

        validator_list = set(prompt_structure.validators or [])
        validator_names = set(map(lambda v: v.name, self._validators))
        if diff := validator_list - validator_names:
            raise MissingValidatorError(*diff)

        structures_list = set(filter(lambda s: isinstance(s, str), prompt_structure.structures or []))
        structure_names = set(map(lambda s: s.name, self._structures))
        if diff := structures_list - structure_names:
            raise MissingStructureError(diff)

    
    @property
    def schemas(self) -> list[Schema]:
        return self._schemas
    
    @property
    def tools(self) -> list[Tool]:
        return self._tools
    
    @property
    def hooks(self) -> list[Hook]:
        return self._hooks
    
    @property
    def validators(self) -> list[Validator]:
        return self._validators

    @property
    def structures(self) -> list[PromptStructure]:
        return self._structures
    
    @property
    def interceptors(self) -> list[Interceptor]:
        return self._interceptors


    async def __complete__(self, name: str, description: str | None, prompt_structure: PromptStructure, args: dict[str, Any]) -> dict[str, Any]:
        inplace_schemas = []
        for s in filter(lambda s: isinstance(s, dict), prompt_structure.schemas or []):
            try:
                inplace_schemas.append(Schema.from_json_schema(**s, schemas=self._schemas + inplace_schemas))
            except KeyError as e:
                raise MissingSchemaError(*e.args)

        inplace_structures = []
        for s in filter(lambda s: isinstance(s, dict), prompt_structure.structures or []):
            inplace_structures.append(PromptStructure.load_from_dict(uuid.uuid4(), s))

        session_id = uuid.uuid4().hex
        await invoke_funcs(
            list(map(lambda i: i.bind_name_with_session, self._interceptors)),
            session_id,
            name,
            description
        )

        structures = self._structures + inplace_structures

        message_list = MessageList.from_prompt_structure(prompt_structure, args=args, structures=structures)

        messages, args, awaited_prompt = message_list.get_messages()

        while awaited_prompt:    
            try:
                awaited_prompt = _Prompt.from_prompt_unit(
                    awaited_prompt,
                    schemas=self._schemas + inplace_schemas,
                    tools=self._tools,
                    hooks=self._hooks,
                    validators=self._validators,
                    structures=structures
                )

                if awaited_prompt.awaited_type == AwaitedType.REQUIRE_CONTENT:    
                    
                    on_response_callbacks = await invoke_funcs(
                        self._interceptors,
                        session_id,
                        messages,
                        args, 
                        awaited_prompt.schema,
                        awaited_prompt.tools,
                        awaited_prompt.hooks,
                        awaited_prompt.validators,
                        awaited_prompt.saves,
                        awaited_prompt.tag
                    )
                    response = await self._generator.get_response(
                        messages, 
                        args, 
                        awaited_prompt.schema, 
                        awaited_prompt.tools, 
                        awaited_prompt.validators, 
                        self._continue_on_max_token, 
                        self._retry_on_rate_limit, 
                        self._retry_with_delay
                    )
                    await invoke_funcs(list(filter(lambda c: c is not None, on_response_callbacks)), response)

                    awaited_prompt.update_content(response.content)
                    
                new_args = await awaited_prompt.invoke(self, args)
                if awaited_prompt.stop_generation:
                    print("StopGeneration exception encountered. Stopping generation.")
                    break

                print("Updating content for ", awaited_prompt.id, response.content)
                message_list.update_content(awaited_prompt.id, response.content, args=new_args)

                messages, args, awaited_prompt = message_list.get_messages()
            except StopGeneration as e:
                break

        await self._generation_queue.get() # Signals a request completed
        return message_list.args
    

    async def __schedule__(self, name: str, description: str | None, prompt_structure: PromptStructure, args: dict[str, Any]) -> dict[str, Any]:
        if self._generation_queue.full():
            print("Generation queue is full. Waiting for a request to complete.")
        async with self._lock:
            queuing_task = asyncio.create_task(self._generation_queue.put(None)) # Wait if max_requests reached
            delay_task = asyncio.create_task(asyncio.sleep(self._delay_constant))  # Delay before processing the request
            await asyncio.gather(queuing_task, delay_task)
        return await self.__complete__(name, description, prompt_structure, args)


    async def execute(self, name: str, description: str | None, prompt_structure: PromptStructure, args: dict[str, Any]) -> dict[str, Any]:
        if prompt_structure.params:
            params = set(map(lambda p: p if isinstance(p, str) else list(p)[0], prompt_structure.params))
            if diff := params - set(args):
                raise MissingParamError(*diff)
        return await self.__schedule__(name, description, prompt_structure, args)

