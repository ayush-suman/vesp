from abc import ABC, abstractmethod
import inspect
from typing import Any, Callable, Sequence
from vespwood.hook import Hook
from vespwood.interceptor import Interceptor
from vespwood.prompt_structure.prompt_structure import PromptStructure
from vespwood.run import Run, RunRestoreData
from vespwood.validator.validator import Validator
from vespwood_generator.generator import Generator
from vespwood_generator.schematic.schema import Schema
from vespwood_generator.schematic.tool import Tool

class Executor(ABC):
    def __init__(
        self,
        schemas: Sequence[Schema] = (),
        tools: Sequence[Tool] = (),
        hooks: Sequence[Hook] = (),
        validators: Sequence[Validator] = (),
        structures: Sequence[PromptStructure] = (),
        continue_on_max_token: bool = True,
        retry_on_rate_limit: bool = True,
        retry_with_delay: int = 0
    ):

        self._schemas: list[Schema] = list(schemas)
        self._tools: list[Tool] = list(tools)
        self._hooks: list[Hook] = list(hooks)
        self._validators: list[Validator] = list(validators)
        self._structures: list[PromptStructure] = list(structures)

        self._continue_on_max_token = continue_on_max_token
        self._retry_on_rate_limit = retry_on_rate_limit
        self._retry_with_delay = retry_with_delay

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # Get the expected signature from the Base class
        expected_sig = inspect.signature(Executor.__init__)
        params = expected_sig.parameters.items()
        # Get the actual signature of the subclass
        actual_sig = inspect.signature(cls.__init__)
        actual_params = actual_sig.parameters.items()
        if actual_params != params:
            raise TypeError(
                f"Subclass '{cls.__name__}' must match the __init__ schema: {expected_sig}"
            )

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

    @abstractmethod
    def execute(
        self, 
        name: str, 
        description: str | None, 
        prompt_structure: PromptStructure, 
        args: dict[str, Any], 
        generator: type[Generator] | Callable[[], Generator], 
        *, 
        extras: dict[str, Any] = {},
        interceptors: Sequence[Interceptor] = ()
    ) -> Run[dict[str, Any]]:
        ...

    @abstractmethod
    def resume_with(self, run_restore_data: RunRestoreData) -> Run[dict[str, Any]]:
        ...