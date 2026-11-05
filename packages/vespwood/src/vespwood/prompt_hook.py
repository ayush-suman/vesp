import inspect
from pathlib import Path
from typing import Any, Callable, Generic, ParamSpec, overload
import uuid

from vespwood.errors.missing_schema_error import MissingSchemaError
from vespwood.executors.executor import Executor
from vespwood.interceptor import Interceptor
from vespwood.prompt_structure.prompt_structure import PromptStructure
from vespwood.validator.validator import Validator
from vespwood_generator.generator import Generator
from vespwood_generator.schematic.schema import Schema
from vespwood_generator.schematic.schematic import Schematic
from vespwood_generator.schematic.tool import Tool

from .hook import Hook


I = ParamSpec("I")
class PromptHook(Hook[I], Generic[I]):
    @overload
    def __init__(self, structure: PromptStructure, executor: Executor, output: list[str], name: str | None = None, description: str | None = None): ...
    @overload
    def __init__(self, structure: PromptStructure, executor: Executor, output: Callable[[dict[str, Any]], dict[str, Any]], name: str | None = None, description: str | None = None): ...
    def __init__(self, structure: PromptStructure, executor: Executor, output: list[str] | Callable[[dict[str, Any]], dict[str, Any]], name: str | None = None, description: str | None = None):
        super().__init__(name or structure.name, description or structure.description)
        self._prompt_structure = structure
        if isinstance(output, list):
            self._output = lambda args: { key: value for key, value in args.items() if key in output }
        else:
            self._output = output 
        self._executor = executor
        for param in self._prompt_structure.params:
            self.add_param(param if isinstance(param, str) else param["name"], Any)

    def copy(self) -> "PromptHook[I]":
        return PromptHook(
            structure=self._prompt_structure,
            executor=self._executor,
            output=self._output,
            name=self.name,
            description=self.description
        )

    async def __call__(self, generator_factory: Callable[[], Generator], interceptors: list[Interceptor] = [], *_: I.args, **kwds: I.kwargs) -> dict[str, Any]:
        output = await self._executor.execute(self.name, self.description, self._prompt_structure, kwds, generator_factory, interceptors=interceptors)
        return self._output(output)


def prompthook(
    prompt_structure: PromptStructure | dict | list | str, 
    executor: type[Executor],
    name: str | None = None, 
    description: str | None = None,
    structures: list[PromptStructure | dict | list | str] = [],
    schemas: list[Schema] = [],
    tools: list[Tool] = [], 
    hooks: list[Hook] = [],
    validators: list[Validator] = [],
    continue_on_max_token: bool = True,
    retry_on_rate_limit: bool = True,
    retry_with_delay: float = 0,
    **executor_args
):
    def to_prompt_structure(structure: PromptStructure | dict | list | str) -> PromptStructure:
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
            return PromptStructure.load_from_file(uuid.uuid4(), structure)
        elif isinstance(structure, dict):
            return PromptStructure.load_from_dict(uuid.uuid4(), structure)
        elif isinstance(structure, list):
            return PromptStructure.load_from_list(
                uuid.uuid4(),
                structure,
                name=id.hex,
            )
    def wrapper(output_callback: Callable[[dict[str, Any]], dict[str, Any]]):
        _executor = executor(
            schemas=schemas, 
            tools=tools, 
            hooks=hooks, 
            validators=validators, 
            structures=structures, 
            continue_on_max_token=continue_on_max_token, 
            retry_on_rate_limit=retry_on_rate_limit, 
            retry_with_delay=retry_with_delay,
            **executor_args
        )
        return PromptHook[...](
            to_prompt_structure(prompt_structure), 
            _executor,
            output=output_callback, 
            name=name, 
            description=description
        )
    return wrapper
