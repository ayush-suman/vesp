import inspect
from pathlib import Path
from typing import Any, TextIO
import asyncio
from vespwood.types.prepared_args import PreparedArgs
from vespwood.generator import Generator
from vespwood._utils import invoke_funcs
from vespwood.interceptor import Interceptor
from vespwood.format_object import FormatKeys
from vespwood.blocks import Structured, ToolCall
from vespwood.tagged_messages import TaggedMessages
from vespwood.hook import Hook
from vespwood.schematic import Schema, Tool
from vespwood.errors import StopGeneration, MissingParamError, MissingSchemaError, MissingToolError, MissingHookError, MissingValidatorError
from vespwood.message import Prompt, Response
from vespwood.validator import Validator
from vespwood.prompt_structure import PromptStructure, MessageList
from vespwood.types.hooks_list import HooksList

import bisect


class Completor:
    __slots__ = "_generator", "_prompt_structure", "_name", "_description", "_params", "_transforms", "_schemas", "_tools", "_hooks", "_validators", "_interceptors", "_delay_constant", "_max_requests", "_generation_queue", "_lock", "_continue_on_max_token", "_retry_on_rate_limit", "_retry_with_delay",

    def __init__(self,
                generator: Generator,
                *,
                prompt_structure: PromptStructure | dict | list | str | None = None,
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
            file: TextIO = open(prompt_structure, "r")
            # Load from JSON file
            if prompt_structure.endswith(".json"):
                import json
                prompt_structure = json.load(file)
            # Load from YAML file
            elif prompt_structure.endswith(".yaml"):
                try:
                    import yaml
                    prompt_structure = yaml.safe_load(file)
                except ImportError as e:
                    raise ImportError(
                        "Importing from yaml requires vespwood[yaml]. "
                        "Install it with: pip install vespwood[yaml]"
                    ) from e
        
        if isinstance(prompt_structure, dict):
            self._name: str = prompt_structure.get("name", "")
            self._description: str | None = prompt_structure.get("description")
            self._params: list[str] = prompt_structure.get("params")
            self._transforms: list = prompt_structure.get("transforms")
            
            schema_list = prompt_structure.get("schemas", [])
            schema_names = set(map(lambda s: s.name, schemas))
            if diff := set(filter(lambda s: isinstance(s, str), schema_list)) - schema_names:
                raise MissingSchemaError(diff)
            for s in filter(lambda s: isinstance(s, dict), schema_list):
                schemas.append(Schema.from_json_schema(**s, schemas=schemas))
            schemas.sort(key=lambda s: s.name)
            self._schemas: list[Schema] = schemas

            tools.sort(key=lambda t: t.name)
            tool_list = set(prompt_structure.get("tools", []))
            tool_names = set(map(lambda t: t.name, tools))
            if diff := tool_list - tool_names:
                raise MissingToolError(diff)
            self._tools: list[Tool] = tools

            hooks.sort(key=lambda h: h.name)
            hook_list = set(prompt_structure.get("hooks", []))
            hook_names = set(map(lambda h: h.name, hooks))
            if diff := hook_list - hook_names:
                raise MissingHookError(diff)
            self._hooks: list[Hook] = hooks

            validators.sort(key=lambda h: h.name)
            validator_list = set(prompt_structure.get("validators", []))
            validator_names = set(map(lambda v: v.name, validators))
            if diff := validator_list - validator_names:
                raise MissingValidatorError(diff)
            self._validators: list[Hook] = validators

            prompt_structure = prompt_structure["structure"]
        else:
            self._name = ""
            self._description = None
            self._params = None
            self._transforms = None
            schemas.sort(key=lambda s: s.name)
            self._schemas = schemas
            tools.sort(key=lambda t: t.name)
            self._tools = tools
            hooks.sort(key=lambda h: h.name)
            self._hooks = hooks
            validators.sort(key=lambda h: h.name)
            self._validators = validators
        self._generator = generator
        self._prompt_structure = PromptStructure.load_from_dict(prompt_structure)
        self._interceptors = interceptors
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
    def params(self) -> list[str]:
        return self._params or []
    
    @property
    def transforms(self) -> list[dict]:
        return self._transforms
    
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


    def _invoke_hooks(self, hooks: HooksList, response: Response, messages: TaggedMessages, format_keys: FormatKeys) -> dict[str, Any]:
        new_keys = {}            
        for hook in hooks:
            if isinstance(hook, str):
                i = bisect.bisect_left(self.hooks, hook, key=lambda h: h.name)
                if i == len(self.hooks) or self.hooks[i].name != hook:
                    raise MissingHookError([hook])
                k = self.hooks[i](response, messages, format_keys.copy_with_extra(**new_keys))
                if k: new_keys.update(k)
            elif isinstance(hook, dict):
                i = bisect.bisect_left(self.hooks, hook["name"], key=lambda h: h.name)
                if i == len(self.hooks) or self.hooks[i].name != hook["name"]:
                    raise MissingHookError([hook["name"]])
                k = self.hooks[i](response, messages, format_keys.copy_with_extra(**new_keys), **(hook["args"] if "args" in hook else {}))
                if k: new_keys.update(k)
        return new_keys
    

    async def __complete__(self, prepared_args: PreparedArgs) -> tuple[TaggedMessages, FormatKeys]:
        message_list = MessageList.from_prompt_structure(self._prompt_structure, keys=prepared_args)
        prompts, tag, schema, tools, hooks, validators, saves = message_list.get_prompt_list()
        while tag:
            on_response_callbacks = await invoke_funcs(
                self._interceptors,
                prompts, 
                tag, 
                schema, 
                tools, 
                hooks, 
                validators, 
                saves, 
                message_list.format_keys
            )
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
                    _schema = Schema.from_json_schema(schema["name"], schema.get("json_schema"), description=schema.get("description"), schemas=self.schemas)

            _tools = []
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
                        i = bisect.bisect_left(self.tools, tool["name"], key=lambda t: t.name)
                        if i == len(self.tools) or self.tools[i].name != tool["name"]:
                            _missing_tools.append(tool["name"])
                        else:
                            _tool = self.tools[i]
                        _tool.update_with(description=tool.get("description"), schema=tool.get("schema"))
                    _tools.append(_tool)
                if _missing_tools:
                    raise MissingToolError(_missing_tools)

            _validators = []
            if validators:
                for validator in validators:
                    i = bisect.bisect_left(self.validators, validator, key=lambda v: v.name)
                    if i == len(self.validators) or self.validators[i] != validator:
                        raise MissingHookError([validator])
                    _validator = self.validators[i]
                    _validators.append(_validator)
             
            try:
                response = await self._generator.get_response(
                    prompts, 
                    _schema, 
                    _tools, 
                    _validators, 
                    self._continue_on_max_token, 
                    self._retry_on_rate_limit, 
                    self._retry_with_delay,
                    **message_list.format_keys, 
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
                    keys = self._invoke_hooks(hooks, response, message_list.tagged_messages, message_list.format_keys)
                    message_list.add_keys(keys)
                prompts, tag, schema, tools, hooks, validators, saves = message_list.get_prompt_list()
                print("Received tag", tag)

            except StopGeneration as e:
                if e.response: 
                    message_list.add_response(response, keys=saved_keys)
                    if hooks:
                        keys = self._invoke_hooks(hooks, e.response, message_list.tagged_messages, message_list.format_keys)
                        message_list.add_keys(keys)
                await self._generation_queue.get()
                return message_list.tagged_messages, message_list.format_keys
            
        await self._generation_queue.get() # Signals a request completed
        return message_list.tagged_messages, message_list.format_keys
    

    async def __schedule__(self, prepared_args: PreparedArgs) -> tuple[TaggedMessages, FormatKeys]:
        if self._generation_queue.full():
            print("Generation queue is full. Waiting for a request to complete.")
        async with self._lock:
            queuing_task = asyncio.create_task(self._generation_queue.put(None)) # Wait if max_requests reached
            delay_task = asyncio.create_task(asyncio.sleep(self._delay_constant))  # Delay before processing the request
            await asyncio.gather(queuing_task, delay_task)
        print("Scheduling request with args: ", prepared_args)
        return await self.__complete__(prepared_args=prepared_args)


    async def __call__(self, args: PreparedArgs) -> tuple[TaggedMessages, FormatKeys]:
        if diff := set(self.params) - set(args):
            raise MissingParamError(*diff)
        print("Invoking ", self.name)
        return await self.__schedule__(args)
