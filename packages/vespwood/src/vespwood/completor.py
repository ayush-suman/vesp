import inspect
from pathlib import Path
from typing import Any
import uuid
import asyncio
from vespwood_generator import (
    Generator,
    Schema, Tool,
    Validator,
    Response,
    Structured, ToolCall
)
from vespwood.types import PreparedArgs, HooksList, Params
from vespwood._utils import invoke_funcs
from vespwood.interceptor import Interceptor
# from vespwood._format_object import FormatKeys
from vespwood.tagged_messages import TaggedMessages
from vespwood.hook import Hook
from vespwood.prompt_structure import PromptStructure, MessageList
from vespwood.errors import StopGeneration, MissingParamError, MissingSchemaError, MissingToolError, MissingHookError, MissingValidatorError
import bisect


class Completor:
    __slots__ = "_generator", "_prompt_structure", "_name", "_description", "_params", "_schemas", "_tools", "_hooks", "_validators", "_interceptors", "_delay_constant", "_max_requests", "_generation_queue", "_lock", "_continue_on_max_token", "_retry_on_rate_limit", "_retry_with_delay",

    def __init__(self,
                generator: Generator,
                *,
                prompt_structure: PromptStructure | dict | list | str,
                name: str | None = None,
                description: str | None = None,
                schemas: list[Schema] = [],
                tools: list[Tool] = [],
                hooks: list[Hook] = [],
                validators: list[Validator] = [],
                interceptors: list[Interceptor] = [],
                delay_constant: int = 0,
                max_requests: int = 0,
                continue_on_max_token: bool = True,
                retry_on_rate_limit: bool = True,
                retry_with_delay: int = 0,
                **kwargs
            ):
        if isinstance(prompt_structure, str):
            # Convert relative path to absolute path
            caller_frame = inspect.stack()[1]
            src_file = caller_frame.filename
            path = Path(prompt_structure)
            if not path.is_absolute() and not path.is_file():
                path = (Path(src_file).parent / path)
                prompt_structure = str(path)
            self._prompt_structure = PromptStructure.load_from_file(prompt_structure)
        
        elif isinstance(prompt_structure, dict):
            self._prompt_structure = PromptStructure.load_from_dict(prompt_structure)

        elif isinstance(prompt_structure, list):
            self._prompt_structure = PromptStructure.to_prompt_list(prompt_structure)

        elif isinstance(prompt_structure, PromptStructure):
            self._prompt_structure = prompt_structure
        self._name: str = name or self._prompt_structure.name
        self._description: str | None = description or self._prompt_structure.description
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
        self._generator: Generator = generator
        self._interceptors: list[Interceptor] = interceptors
        self._delay_constant: int = delay_constant
        self._max_requests: int = max_requests
        
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


    def _invoke_hooks(self, hooks: HooksList, response: Response, messages: TaggedMessages, format_keys: dict) -> dict[str, Any]:
        new_keys = {}
        for hook in hooks:
            if isinstance(hook, str):
                i = bisect.bisect_left(self.hooks, hook, key=lambda h: h.name)
                if i == len(self.hooks) or self.hooks[i].name != hook:
                    raise MissingHookError([hook])
                k = self.hooks[i](response, messages, format_keys | new_keys)
                if k: new_keys.update(k)
            elif isinstance(hook, dict):
                i = bisect.bisect_left(self.hooks, hook["name"], key=lambda h: h.name)
                if i == len(self.hooks) or self.hooks[i].name != hook["name"]:
                    raise MissingHookError([hook["name"]])
                k = self.hooks[i](response, messages, format_keys | new_keys, **(hook.get("args", {})))
                if k: new_keys.update(k)
        return new_keys
    

    async def __complete__(self, prepared_args: PreparedArgs) -> tuple[TaggedMessages, dict[str, Any]]:
        session_id = uuid.uuid4().hex
        print("Name: ", self._name, "Session ID: ", session_id)
        await invoke_funcs(
            list(map(lambda i: i.bind_name_with_session, self._interceptors)),
            session_id,
            self._name,
            self._description
        )
        message_list = MessageList.from_prompt_structure(self._prompt_structure, keys=prepared_args)
        prompts, format_keys, tag, schema, tools, hooks, validators, saves = message_list.get_prompt_list()
        print("Received tag", tag)
        while tag:
            for prompt in prompts:
                for block in prompt:
                    if isinstance(block, ToolCall) and block.result is None:
                        i = bisect.bisect_left(self.tools, block.name, key=lambda t: t.name)
                        if i == len(self.tools) or self.tools[i].name != block.name:
                            raise MissingToolError([block.name])
                        result = self.tools[i](**block.arguments)
                        block.add_result(result)
            
            _schema = None
            if schema:
                if isinstance(schema, str):
                    i = bisect.bisect_left(self.schemas, schema, key=lambda s: s.name)
                    if i == len(self.schemas) or self.schemas[i].name != schema:
                        raise MissingSchemaError([schema])
                    _schema = self.schemas[i]
                else:
                    try:
                        _schema = Schema.from_json_schema(schema["name"], schema.get("json_schema"), description=schema.get("description"), schemas=self.schemas)
                    except KeyError as e:
                        raise MissingSchemaError([*e.args]) 

            _tools: list[Tool] = []
            if tools:
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
                            class PromptTool(Tool):
                                def __init__(inner_self, name: str, description: str, schema: Schema, structure: PromptStructure, output: dict[str, str], generator: Generator):
                                    inner_self._completer = Completor(
                                        generator, 
                                        prompt_structure=structure, 
                                        name=name, 
                                        description=description, 
                                        schemas=self.schemas, 
                                        tools=self.tools, 
                                        hooks=self.hooks, 
                                        validators=self.validators,
                                        interceptors=self.interceptors,
                                        continue_on_max_token=self._continue_on_max_token,
                                        retry_on_rate_limit=self._retry_on_rate_limit,
                                        retry_with_delay=self._retry_with_delay
                                    )
                                    inner_self._schema = schema.schema
                                    inner_self._output = output

                                async def __call__(self, **kwargs) -> dict[str, Any]:
                                    _, format_keys = await self._completer(kwargs)
                                    output = {}
                                    for key, value in self._output.items():
                                        output[value] = format_keys[key]
                                    return output
                                
                            _tool = PromptTool(
                                tool.get("name"), 
                                tool.get("description"), 
                                Schema.from_json_schema(
                                    name=tool["schema"]["name"],
                                    description=tool["schema"]["description"],
                                    json_schema=tool["schema"]["json_schema"],
                                    schemas=self.schemas
                                ),
                                PromptStructure.load_from_dict(tool["structure"]),
                                tool["output"],
                                self._generator
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

            _validators = []
            if validators:
                for validator in validators:
                    i = bisect.bisect_left(self.validators, validator, key=lambda v: v.name)
                    if i == len(self.validators) or self.validators[i].name != validator:
                        raise MissingValidatorError([validator])
                    _validator = self.validators[i]
                    _validators.append(_validator)
             
            try:
                on_response_callbacks = await invoke_funcs(
                    self._interceptors,
                    session_id,
                    prompts,
                    format_keys, 
                    tag, 
                    _schema, 
                    _tools, 
                    hooks, 
                    _validators, 
                    saves
                )
                response = await self._generator.get_response(
                    prompts, 
                    format_keys, 
                    _schema, 
                    _tools, 
                    _validators, 
                    self._continue_on_max_token, 
                    self._retry_on_rate_limit, 
                    self._retry_with_delay,
                ) @ tag
                await invoke_funcs(list(filter(lambda c: c is not None, on_response_callbacks)), response)
                saved_keys = {}
                if saves:
                    for k, v in saves.items():
                        for content in response:
                            if isinstance(content, Structured):
                                saved_keys[v] = content[k]
                message_list.add_response(response, keys=saved_keys)
                if hooks:
                    keys = self._invoke_hooks(hooks, response, message_list.tagged_messages, format_keys)
                    message_list.add_keys(keys)

                prompts, format_keys, tag, schema, tools, hooks, validators, saves = message_list.get_prompt_list()
                print("Received tag", tag)

            except StopGeneration as e:
                await self._generation_queue.get()
                return message_list.tagged_messages, message_list.format_keys
            
        await self._generation_queue.get() # Signals a request completed
        return message_list.tagged_messages, message_list.format_keys
    

    async def __schedule__(self, prepared_args: PreparedArgs) -> tuple[TaggedMessages, dict[str, Any]]:
        if self._generation_queue.full():
            print("Generation queue is full. Waiting for a request to complete.")
        async with self._lock:
            queuing_task = asyncio.create_task(self._generation_queue.put(None)) # Wait if max_requests reached
            delay_task = asyncio.create_task(asyncio.sleep(self._delay_constant))  # Delay before processing the request
            await asyncio.gather(queuing_task, delay_task)
        return await self.__complete__(prepared_args=prepared_args)


    async def __call__(self, args: PreparedArgs) -> tuple[TaggedMessages, dict[str, Any]]:
        if self.params:
            params = set(map(lambda p: p if isinstance(p, str) else list(p)[0], params))
            if diff := params - set(args):
                raise MissingParamError(*diff)
            print("Invoking ", self.name)
        return await self.__schedule__(args)