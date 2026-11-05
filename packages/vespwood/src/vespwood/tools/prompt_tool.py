import inspect
from pathlib import Path
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar, Generic, overload
import uuid
from vespwood.errors.missing_schema_error import MissingSchemaError
from vespwood.executors.executor import Executor
from vespwood.hook import Hook
from vespwood.interceptor import Interceptor
from vespwood.prompt_structure.prompt_structure import PromptStructure
from vespwood.validator.validator import Validator
from vespwood_generator import Tool
from vespwood_generator.generator import Generator
from vespwood_generator.schematic import Schematic, Schema


I = ParamSpec("I")
O = TypeVar("O")
class PromptTool(Tool[I, Awaitable[O]], Generic[I, O]):
    @overload
    def __init__(self, structure: PromptStructure, executor: Executor, schema: Schematic, output: list[str], name: str | None = None, description: str | None = None): ...
    @overload
    def __init__(self, structure: PromptStructure, executor: Executor, schema: Schematic, output: Callable[[dict[str, Any]], O], name: str | None = None, description: str | None = None): ...
    def __init__(self, structure: PromptStructure, executor: Executor, schema: Schematic, output: list[str] | Callable[[dict[str, Any]], O], name: str | None = None, description: str | None = None):
        super().__init__(name or structure.name, description or structure.description, schema)
        self._prompt_structure = structure
        self._executor = executor
        if isinstance(output, list):
            self._output = lambda args: { key: value for key, value in args.items() if key in output }
        else:
            self._output = output 

    def copy(self) -> "PromptTool[I, O]":
        return PromptTool(
            structure=self._prompt_structure,
            executor=self._executor,
            schema=self._schema,
            output=self._output,
            name=self._name,
            description=self._description
        )

    def copy_with(self, *, name = None, description = None, schema) -> "PromptTool[I, O]":
        return PromptTool(
            structure=self._prompt_structure,
            executor=self._executor,
            schema=schema or self._schema,
            output=self._output,
            name=name or self._name,
            description=description or self._description
        )

    async def __call__(self, generator_factory: Callable[[], Generator], interceptors: list[Interceptor] = [], *_: I.args, **kwds: I.kwargs) -> O:
        output = await self._executor.execute(self._name, self._description, self._prompt_structure, kwds, generator_factory, interceptors=interceptors)
        return self._output(output)


def prompttool(
    prompt_structure: PromptStructure | dict | list | str, 
    executor: type[Executor], 
    schema: Schematic, 
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
    def wrapper(output_callback: Callable[[dict[str, Any]], O]):
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
        return PromptTool[..., O](to_prompt_structure(prompt_structure), _executor, schema, output=output_callback, name=name, description=description, schema=schema)
    return wrapper


