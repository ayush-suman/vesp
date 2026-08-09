import inspect
from pathlib import Path
from typing import Any, Generic, ParamSpec, TypeVar, get_type_hints
import uuid
import asyncio
from vespwood.hook_tool import HookTool
from vespwood_generator import (
    Generator,
    Message,
    Schema,
    StopGeneration, Tool,
    Validator,
    Structured, ToolCall
)
from vespwood.prompt import Prompt, AwaitedType
from vespwood.types import PreparedArgs, HooksList, Params
from vespwood._utils import filter_params, invoke_funcs, suppliment_args
from vespwood.interceptor import Interceptor
from vespwood.hook import Hook
from vespwood.prompt_structure import PromptStructure, MessageList
from vespwood.errors import MissingParamError, MissingSchemaError, MissingToolError, MissingHookError, MissingValidatorError
import bisect



I = ParamSpec("I")
O = TypeVar("O", bound=dict)
class Completor(Tool[I, O], Generic[I, O]):
    __slots__ = "_generator", "_prompt_structure", "_name", "_description", "_params", "_schemas", "_tools", "_hooks", "_validators", "_interceptors", "_output", "_delay_constant", "_max_requests", "_generation_queue", "_lock", "_continue_on_max_token", "_retry_on_rate_limit", "_retry_with_delay",

    def __init__(self,
                generator: Generator,
                *,
                prompt_structure: PromptStructure | dict | list | str,
                name: str | None = None,
                description: str | None = None,
                schema: Schema | None = None,
                schemas: list[Schema] = [],
                tools: list[Tool] = [],
                hooks: list[Hook] = [],
                validators: list[Validator] = [],
                interceptors: list[Interceptor] = [],
                structures: list[PromptStructure | dict | list | str],
                output: list[str | dict[str, str]] | None = None,
                delay_constant: int = 0,
                max_requests: int = 0,
                continue_on_max_token: bool = True,
                retry_on_rate_limit: bool = True,
                retry_with_delay: int = 0,
                **kwargs
            ):
        def to_prompt_structure(structure: PromptStructure | dict | list | str):
            if isinstance(structure, PromptStructure):
                return structure
            elif isinstance(structure, str):
                # Convert relative path to absolute path
                caller_frame = inspect.stack()[1]
                src_file = caller_frame.filename
                path = Path(structure)
                if not path.is_absolute() and not path.is_file():
                    path = (Path(src_file).parent / path)
                    structure = str(path)
                return PromptStructure.load_from_file(structure)
            elif isinstance(structure, dict):
                return PromptStructure.load_from_dict(structure)
            elif isinstance(structure, list):
                return PromptStructure.to_prompt_list(structure)
        self._prompt_structure = to_prompt_structure(prompt_structure)
        super().__init__(name or self._prompt_structure.name, description or self._prompt_structure.description, schema)

        self._params: Params | None = self._prompt_structure.params

        schema_list = self._prompt_structure.schemas or []
        schema_names = set(map(lambda s: s.name, schemas))
        if diff := set(filter(lambda s: isinstance(s, str), schema_list)) - schema_names:
            raise MissingSchemaError(diff)
        for s in filter(lambda s: isinstance(s, dict), schema_list):
            try:
                schemas.append(Schema.from_json_schema(**s, schemas=schemas))
            except KeyError as e:
                raise MissingSchemaError([*e.args])
        schemas.sort(key=lambda s: s.name)
        self._schemas: list[Schema] = schemas

        tools.sort(key=lambda t: t.name)
        tool_list = set(self._prompt_structure.tools or [])
        tool_names = set(map(lambda t: t.name, tools))
        if diff := tool_list - tool_names:
            raise MissingToolError(diff)
        self._tools: list[Tool] = tools

        hooks.sort(key=lambda h: h.name)
        hook_list = set(self._prompt_structure.hooks or [])
        hook_names = set(map(lambda h: h.name, hooks))
        if diff := hook_list - hook_names:
            raise MissingHookError(diff)
        self._hooks: list[Hook] = hooks

        validators.sort(key=lambda h: h.name)
        validator_list = set(self._prompt_structure.validators or [])
        validator_names = set(map(lambda v: v.name, validators))
        if diff := validator_list - validator_names:
            raise MissingValidatorError(diff)
        self._validators: list[Hook] = validators

        self._structures = [to_prompt_structure(structure) for structure in structures]

        self._generator: Generator = generator
        self._interceptors: list[Interceptor] = interceptors
        self._delay_constant: int = delay_constant
        self._max_requests: int = max_requests
        self._output: list[str | dict[str, str]] = output
        self._generation_queue: asyncio.Queue = asyncio.Queue(maxsize=max_requests or 0)
        self._lock = asyncio.Lock()

        self._continue_on_max_token = continue_on_max_token
        self._retry_on_rate_limit = retry_on_rate_limit,
        self._retry_with_delay = retry_with_delay
    

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str | None:
        return self._description
    
    @property
    def params(self) -> Params | None:
        return self._params
    
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
    def interceptors(self) -> list[Interceptor]:
        return self._interceptors


    def _invoke_hooks(self, hooks: HooksList, message: Message, args: dict[str, Any]) -> dict[str, Any]:
        new_args = {}
        for hook in hooks:
            hook_name = hook if isinstance(hook, str) else hook["name"]
            i = bisect.bisect_left(self.hooks, hook_name, key=lambda h: h.name)
            if i == len(self.hooks) or self.hooks[i].name != hook_name:
                raise MissingHookError([hook_name])
            hook = suppliment_args(self.hooks[i], skip_params=["message"], args=args)
            returned_args = hook(message)
            if returned_args: 
                new_args.update(returned_args)
                args.update(returned_args)
        return new_args


    async def _invoke_tools(self, message: Message, args: dict[str, Any]) -> dict[str, Any]:
        new_args = {}
        for block in message:
            if isinstance(block, ToolCall) and block.result is None:
                i = bisect.bisect_left(self.tools, block.name, key=lambda t: t.name)
                if i == len(self.tools) or self.tools[i].name != block.name:
                    raise MissingToolError([block.name])
                result = None
                if isinstance(self.tools[i], HookTool):
                    hooktool = suppliment_args(self.tools[i], skip_params=["message"], **args)
                    returned_args, result = await hooktool(message, **block.arguments)
                    if returned_args:
                        new_args.update(returned_args)
                        args.update(returned_args)
                else:
                    result = self.tools[i](**block.arguments)
                if result and inspect.isawaitable(result):
                    result = await result
                block.add_result(result)
        return new_args


    def _load_schema(self, schema: str | dict) -> Schema | None:
        if isinstance(schema, str):
            i = bisect.bisect_left(self.schemas, schema, key=lambda s: s.name)
            if i == len(self.schemas) or self.schemas[i].name != schema:
                raise MissingSchemaError([schema])
            return self.schemas[i]
        else:
            try:
                return Schema.from_json_schema(schema["name"], schema.get("json_schema"), description=schema.get("description"), schemas=self.schemas)
            except KeyError as e:
                raise MissingSchemaError([*e.args])


    def _load_tools(self, tools: list[str | dict]) -> list[Tool]:
        _tools: list[Tool] = []
        _missing_tools = [] 
        for tool in tools:
            _tool: Tool
            if isinstance(tool, str):
                i = bisect.bisect_left(self.tools, tool, key=lambda t: t.name)
                if i == len(self.tools) or self.tools[i].name != tool:
                    _missing_tools.append(tool)
                else:
                    _tool = self.tools[i]
            elif isinstance(tool, dict):
                if "structure" in tool:
                    _tool = Completor(
                        self._generator,
                        prompt_structure = PromptStructure.load_from_dict(tool["structure"]),
                        name = tool.get("name"), 
                        description = tool.get("description"), 
                        schema = Schema.from_json_schema(
                            name=tool["schema"]["name"],
                            description=tool["schema"]["description"],
                            json_schema=tool["schema"]["json_schema"],
                            schemas=self.schemas
                        ),
                        schemas=self.schemas, 
                        tools=self.tools, 
                        hooks=self.hooks, 
                        validators=self.validators,
                        interceptors=self.interceptors,
                        continue_on_max_token=self._continue_on_max_token,
                        retry_on_rate_limit=self._retry_on_rate_limit,
                        retry_with_delay=self._retry_with_delay,
                        output = tool["output"]
                    )
                else:
                    i = bisect.bisect_left(self.tools, tool["name"], key=lambda t: t.name)
                    if i == len(self.tools) or self.tools[i].name != tool["name"]:
                        _missing_tools.append(tool["name"])
                    else:
                        _tool = self.tools[i]
                    
                    _tool = _tool.copy_with(
                        description=tool.get("description"), 
                        schema=Schema.from_json_schema(
                            name=tool["schema"]["name"],
                            description=tool["schema"]["description"],
                            json_schema=tool["schema"]["json_schema"],
                            schemas=self.schemas
                        ) if "schema" in tool else None)
            _tools.append(_tool)
        if _missing_tools:
            raise MissingToolError(_missing_tools)
        return _tools


    def _load_validators(self, validators: list[str | dict]) -> list[Validator]:
        _validators = []
        for validator in validators:
            if isinstance(validator, str):
                i = bisect.bisect_left(self.validators, validator, key=lambda v: v.name)
                if i == len(self.validators) or self.validators[i].name != validator:
                    raise MissingValidatorError([validator])
                _validators.append(self.validators[i])
            elif isinstance(validator, dict):
                i = bisect.bisect_left(self.validators, validator["name"], key=lambda v: v.name)
                if i == len(self.validators) or self.validators[i].name != validator["name"]:
                    raise MissingValidatorError([validator["name"]])
                _validators.append(self.validators[i])
        return _validators


    async def __complete__(self, **args: I.kwargs) -> dict[str, Any]:
        session_id = uuid.uuid4().hex
        await invoke_funcs(
            list(map(lambda i: i.bind_name_with_session, self._interceptors)),
            session_id,
            self._name,
            self._description
        )

        message_list = MessageList.from_prompt_structure(self._prompt_structure, args=args)

        messages, args, awaited_prompt = message_list.get_prompt_list() # Should return awaited_prompt if no content or tool call without call result

        while awaited_prompt:    
            try:
                if awaited_prompt.awaited_type == AwaitedType.REQUIRE_CONTENT:
                    _schema = self._load_schema(awaited_prompt.schema) if awaited_prompt.schema else None
                    _tools: list[Tool] = self._load_tools(awaited_prompt.tools) if awaited_prompt.tools else []
                    _validators = self._load_validators(awaited_prompt.validators) if awaited_prompt.validators else []
                
                    on_response_callbacks = await invoke_funcs(
                        self._interceptors,
                        session_id,
                        messages,
                        args, 
                        awaited_prompt
                    )
                    response = await self._generator.get_response(
                        messages, 
                        args, 
                        _schema, 
                        _tools, 
                        _validators, 
                        self._continue_on_max_token, 
                        self._retry_on_rate_limit, 
                        self._retry_with_delay
                    )

                    await invoke_funcs(list(filter(lambda c: c is not None, on_response_callbacks)), response)

                    awaited_prompt.update_content(response.content)

                new_args = await self._invoke_tools(response, args=args)

                if _schema:
                    new_args.update(awaited_prompt.saved_args)
                    if awaited_prompt.is_tagged:
                        payload = _schema.load(list(filter(lambda b: isinstance(b, dict), response.content))[0])
                        new_args.update({ awaited_prompt.tag: payload })


                if awaited_prompt.hooks:
                    new_args |= self._invoke_hooks(awaited_prompt.hooks, response, args)

                message_list.update_message(awaited_prompt.id, response, args=args)

                messages, args, awaited_prompt = message_list.get_prompt_list()

            except StopGeneration as e:
                break

        await self._generation_queue.get() # Signals a request completed
        return message_list.args
    

    async def __schedule__(self, **args: I.kwargs) -> O:
        if self._generation_queue.full():
            print("Generation queue is full. Waiting for a request to complete.")
        async with self._lock:
            queuing_task = asyncio.create_task(self._generation_queue.put(None)) # Wait if max_requests reached
            delay_task = asyncio.create_task(asyncio.sleep(self._delay_constant))  # Delay before processing the request
            await asyncio.gather(queuing_task, delay_task)
        response = await self.__complete__(args=args)
        if self._output:
            output: O = {}
            for key in self._output:
                value = key if isinstance(key, str) else list(key.values())[0]
                output[value] = response[key]
            return output
        else: 
            return response


    async def __call__(self, **args: I.kwargs) -> O:
        if self.params:
            params = set(map(lambda p: p if isinstance(p, str) else list(p)[0], params))
            if diff := params - set(args):
                raise MissingParamError(*diff)
        return await self.__schedule__(**args)

