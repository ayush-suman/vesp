from __future__ import annotations
import inspect
from typing import Any
from enum import Enum
import uuid
from vespwood._utils import get_arg
from vespwood.errors.missing_structure_error import MissingStructureError
from vespwood.errors.missing_hook_error import MissingHookError
from vespwood.errors.missing_schema_error import MissingSchemaError
from vespwood.errors.missing_tool_error import MissingToolError
from vespwood.errors.missing_validator_error import MissingValidatorError
from vespwood.executors.executor import Executor
from vespwood.prompt_hook import PromptHook
from vespwood.prompt_structure.prompt_structure import PromptStructure
from vespwood.tools.hook_tool import HookTool
from vespwood.prompt_structure.prompt_unit import PromptUnit
from vespwood.tools.prompt_tool import PromptTool
from vespwood_generator import (
    Message,
    File, Image, ToolCall,
    Role,
    Block,
    Schema, Tool, Validator,
    IndexedList
)
from vespwood.tag import Tag
from vespwood.hook import Hook

from vespwood.types import (
    Saves
)
from vespwood_generator.blocks.structured import Structured

class _Prompt(Message):
    __slots__ = "_id", "_tag", "_schema", "_tools", "_hooks", "_validators", "_saves"

    def __init__(self, 
        id: uuid.UUID,
        *,
        role: Role, 
        content: Block | list[Block] | None = None, 
        schema: Schema | None = None, 
        tools: IndexedList[Tool, str] = [],
        hooks: IndexedList[Hook, str] = [],
        validators: IndexedList[Validator, str] = [],
        saves: Saves | None = None,
        tag: str | None = None

    ):
        self._id: uuid.UUID = id
        self._schema: Schema | None = schema
        self._tools: IndexedList[Tool, str] = tools
        self._hooks: IndexedList[Hook, str] = hooks
        self._validators: IndexedList[Validator, str] = validators
        self._saves: Saves | None = saves
        self._tag: Tag = Tag(tag)
        super().__init__(role, content)

    @staticmethod
    def from_prompt_unit(
        prompt_unit: PromptUnit, 
        *, 
        schemas: IndexedList[Schema, str] = IndexedList(key=lambda s: s.name), 
        tools: IndexedList[Tool, str] = IndexedList(key=lambda s: s.name), 
        hooks: IndexedList[Hook, str] = IndexedList(key=lambda s: s.name), 
        validators: IndexedList[Validator, str] = IndexedList(key=lambda s: s.name),
        structures: IndexedList[PromptStructure, str] = IndexedList(key=lambda s: s.name)
    ) -> _Prompt:
        _schema: Schema | None = None
        if prompt_unit.schema:
            if isinstance(prompt_unit.schema, str):
                _schema = schemas.find(prompt_unit.schema)
                if _schema is None:
                    raise MissingSchemaError(prompt_unit.schema)
            else:
                try:
                    _schema = Schema.from_json_schema(
                        prompt_unit.schema["name"], 
                        prompt_unit.schema.get("json_schema"), 
                        description=prompt_unit.schema.get("description"), 
                        schemas=schemas
                    )
                except KeyError as e:
                    raise MissingSchemaError(*e.args)

        _tools: IndexedList[Tool, str] = IndexedList[Tool, str](key=lambda t: t.name)
        if prompt_unit.tools:
            _missing_tools = [] 
            for tool in prompt_unit.tools or []:
                _tool: Tool | None = None
                if isinstance(tool, str):
                    _tool = tools.find(tool)
                    if _tool is None:
                        _missing_tools.append(tool)
                        continue
                elif isinstance(tool, dict):
                    if "structure" in tool:
                        structure = None
                        if isinstance(tool["structure"], str):
                            structure = structures.find(tool["structure"])  
                            if structure is None:
                                raise MissingStructureError(tool["structure"])
                        else:
                            structure = PromptStructure.load_from_dict(uuid.uuid5(uuid.UUID(prompt_unit.id), "tool" + tool["name"]), tool["structure"])

                        _tool = PromptTool(
                            structure=structure,
                            output=tool["output"],
                            name=tool["name"], 
                            description=tool.get("description"), 
                            schema=Schema.from_json_schema(
                                name=tool["schema"]["name"],
                                description=tool["schema"].get("description"),
                                json_schema=tool["schema"]["json_schema"],
                                schemas=schemas
                            )
                        )
                    else:
                        _tool = tools.find(tool["name"])
                        if _tool is None:
                            _missing_tools.append(tool["name"])
                            continue
                        _tool = _tool.copy_with(
                            description=tool.get("description"), 
                            schema=Schema.from_json_schema(
                                name=tool["schema"]["name"],
                                description=tool["schema"].get("description"),
                                json_schema=tool["schema"]["json_schema"],
                                schemas=schemas
                            ) if "schema" in tool else None)
                _tools.insert(_tool)
            if _missing_tools:
                raise MissingToolError(*_missing_tools)

        _hooks: IndexedList[Hook, str] = IndexedList[Hook, str](key=lambda h: h.name)
        if hooks:
            _missing_hooks = []
            for hook in prompt_unit.hooks or []:
                _hook: Hook | None = None
                if isinstance(hook, str):
                    _hook = hooks.find(hook)
                    if _hook is None:
                        _missing_hooks.append(hook)
                        continue
                elif isinstance(hook, dict):
                    if "structure" in hook:
                        structure = None
                        if isinstance(hook["structure"], str):
                            structure = structures.find(hook["structure"]) 
                            if structure is None:
                                raise MissingStructureError(hook["structure"])
                        else:
                            structure = PromptStructure.load_from_dict(uuid.uuid5(uuid.UUID(prompt_unit.id), "hook" + hook["name"]), hook["structure"])
                        _hook = PromptHook(
                            structure=structure,
                            output=hook["output"],
                            name=hook["name"], 
                            description=hook.get("description"), 
                            schema=Schema.from_json_schema(
                                name=hook["schema"]["name"],
                                description=hook["schema"].get("description"),
                                json_schema=hook["schema"]["json_schema"],
                                schemas=schemas
                            )
                        )
                    else:
                        _hook = hooks.find(hook["name"])
                        if _hook is None:
                            _missing_hooks.append(hook["name"])
                            continue
                _hooks.insert(_hook)
            if _missing_hooks:
                raise MissingHookError(*_missing_hooks)

        _validators: IndexedList[Validator, str] = IndexedList[Validator, str](key=lambda v: v.name)
        if validators:
            _missing_validators = []
            for validator in prompt_unit.validators or []:
                validator_name = validator if isinstance(validator, str) else validator["name"]
                _validator = validators.find(validator_name)
                if _validator is None:
                    _missing_validators.append(validator_name)
                    continue
                _validators.insert(_validator)
            if _missing_validators:
                raise MissingValidatorError(*_missing_validators)
        
        return _Prompt(
            uuid.UUID(prompt_unit.id), 
            role=prompt_unit.role, 
            content=prompt_unit.content, 
            schema=_schema, 
            tools=_tools, 
            hooks=_hooks, 
            validators=_validators, 
            saves=prompt_unit.saves, 
            tag=prompt_unit.tag
        )
    

    def copy(self) -> _Prompt:
        return _Prompt(
            self._id,
            role=self._role, 
            content=self._content.copy() if self._content else None, 
            params=self._params.copy() if self._params else None,
            schema=self._schema.copy() if isinstance(self._schema, dict) else self._schema,
            tools=self._tools.copy() if self._tools else None,
            hooks=self._hooks.copy() if self._hooks else None,
            validators=self._validators.copy() if self._validators else None,
            saves=self._saves.copy() if self._saves else None,
            tag=self._tag.copy() if self._tag else None
        )
    
    def __copy__(self) -> _Prompt:
        return self.copy()


    @property
    def id(self) -> str:
        return self._id.hex

    @property
    def schema(self) -> Schema | None:
        return self._schema
    
    @property
    def hooks(self) -> list[Hook]:
        return self._hooks
    
    @property
    def tools(self) -> list[Tool]:
        return self._tools
    
    @property
    def validators(self) -> list[Validator]:
        return self._validators

    @property
    def saves(self):
        return self._saves

    @property
    def tag(self):
        return self._tag
    
    @property
    def is_tagged(self) -> bool:
        return self._tag
    

    async def _invoke_hooks(self, executor: Executor, args: dict[str, Any]) -> dict[str, Any]:
        new_args = {}
        for hook in self.hooks:
            if isinstance(hook, PromptHook) and not hook.has_executor:
                hook = hook.with_executor(executor)
            hook = hook.suppliment(**args)
            returned_args = await hook(self)
            if returned_args: 
                new_args.update(returned_args)
                args.update(returned_args)
        return new_args


    async def _invoke_tools(self, executor: Executor, args: dict[str, Any]) -> dict[str, Any]:
        new_args = {}
        for block in self:
            if isinstance(block, ToolCall) and block.result is None:
                tool = self._tools.find(block.name)
                if tool is None:
                    raise MissingToolError(block.name)
                # Calling Hook Part
                if isinstance(tool, HookTool):
                    merged_args = args | block.arguments
                    hook = tool.hook.suppliment(**merged_args)
                    returned_args = await hook(self)
                    if returned_args:
                        new_args.update(returned_args)
                        args.update(returned_args)
                elif isinstance(tool, PromptTool) and not tool.has_executor:
                    tool = tool.with_executor(executor)
                # Tool Call
                result = tool(**block.arguments)
                if result and inspect.isawaitable(result):
                    result = await result
                block.add_result(result)
        return new_args

    @property
    def _saved_args(self) -> dict[str, Any]:
        new_args = {}
        if self.schema:
            payload = self.schema.load(list(filter(lambda b: isinstance(b, dict), self.content))[0])
            if self.is_tagged:
                new_args.update({ self.tag: payload })
            if self._saves:
                for key in self._saves:
                    new_args.update({self._saves[key]: get_arg(payload, self._key)})
        return new_args

    def update_content(self, content: Block | list[Block]):
        if content is None:
            self._content = None
        elif isinstance(content, (str, Structured, ToolCall, Image, File)):
            self._content = [content]
        elif isinstance(content, list):
            self._content = content
            
    async def invoke(self, executor: Executor, args: dict[str, Any]) -> dict[str, Any]:
        new_args = await self._invoke_tools(executor, args)
        new_args.update(self._saved_args)
        new_args.update(await self._invoke_hooks(executor, args | new_args))
        return new_args

    
