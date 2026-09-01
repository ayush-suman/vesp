import inspect
from pathlib import Path
from typing import Any, Callable, Generic, ParamSpec, overload
import uuid

from vespwood.errors.missing_schema_error import MissingSchemaError
from vespwood.executors.executor import Executor
from vespwood.prompt_structure.prompt_structure import PromptStructure
from vespwood_generator.schematic.schematic import Schematic

from .hook import Hook


I = ParamSpec("I")
class PromptHook(Hook[I], Generic[I]):
    @overload
    def __init__(self, structure: PromptStructure, output: list[str], name: str | None = None, description: str | None = None): ...
    @overload
    def __init__(self, structure: PromptStructure, output: Callable[[dict[str, Any]], dict[str, Any]], name: str | None = None, description: str | None = None): ...
    def __init__(self, structure: PromptStructure, output: list[str] | Callable[[dict[str, Any]], dict[str, Any]], name: str | None = None, description: str | None = None):
        super().__init__(name or structure.name, description or structure.description)
        self._prompt_structure = structure
        if isinstance(output, list):
            self._output = lambda args: { key: value for key, value in args.items() if key in output }
        else:
            self._output = output 
        self._executor: Executor | None = None
        for param in self._prompt_structure.params:
            self.add_param(param if isinstance(param, str) else param["name"], Any)

    @property
    def has_executor(self) -> bool:
        return bool(self._executor)

    def load_executor(self, executor: Executor):
        self._executor = executor

    def with_executor(self, executor: Executor):
        new = self.copy()
        new.load_executor(executor)
        return new

    def copy(self) -> "PromptHook[I]":
        return PromptHook(
            structure=self._prompt_structure,
            output=self._output,
            name=self.name,
            description=self.description
        )

    async def __call__(self, *args: I.args, **kwds: I.kwargs) -> dict[str, Any]:
        args = await self._executor.execute(self._prompt_structure, kwds)
        return self._output(args)


def prompthook(prompt_structure: PromptStructure | dict | list | str, *, name: str | None = None, description: str | None = None, schema: Schematic | None = None):
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
        return PromptHook[...](structure=to_prompt_structure(prompt_structure), output=output_callback, name=name, description=description, schema=schema)
    return wrapper
