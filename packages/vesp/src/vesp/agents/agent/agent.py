import asyncio
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, ParamSpec, TypeVar, Generic
from abc import abstractmethod
import uuid

from vesp.agents import BaseAgent
from vesp.invokation import Invokation
from vespwood import (
    Generator,
    GeneratorClass,
    Interceptor,
    Schema,
    Hook,
    Tool,
    Completor,
    Schematic,
    Validator
)
import inspect

from vespwood.prompt_structure.message_list import PromptStructure
from vespwood_generator import suppliment

I = ParamSpec("I")
O = TypeVar("O")
class Agent(BaseAgent[I, O], Generic[I, O]):
    def __init__(self):
        self._name = self.__class__.__name__
        self._description = self.__doc__
        super().__init__()

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    

    @abstractmethod
    async def invoke(self, args: dict[str, Any]) -> dict[str, Any]:
        '''Accepts args, and returns outputs for the Invokation chain object'''
        ...


    @abstractmethod
    async def handle_responses(self, **kwargs) -> O:
        ...


    def __get_output__(self, kwargs: dict[str, Any], *, future: asyncio.Future | None = None, chain: Invokation[O] | None = None) -> O:
        def on_output(output: O):
            if chain: chain.add_output(output)
            if future: future.set_result(output)
        # Step 3: Handle Response
        handle_responses = suppliment(self.handle_responses, **kwargs)
        handle_responses_task = asyncio.create_task(handle_responses())
        handle_responses_task.add_done_callback(lambda t: on_output(t.result()))
        

    def __call__(self, *_: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        chain = Invokation()
        async def run_with() -> O:
            result = await self.invoke(**kwargs)
            return await self.__get_output__(result, chain=chain)
        task = asyncio.create_task(run_with())
        task.add_done_callback(lambda _: chain.mark_completed())
        return chain

    
    def __str__(self):
        return self._name


    def __repr__(self):
        return self._name


class LocalAgentMixin:
    def __init__(
        self, 
        name: str,
        description: str | None,
        generator: GeneratorClass | Generator,
        prompt_structure: PromptStructure | dict | list | str,
        structures: list[PromptStructure | dict | list | str],
        schemas: list[Schema] = [],
        tools: list[Tool] = [], 
        hooks: list[Hook] = [],
        validators: list[Validator] = [], 
        interceptors: list[Interceptor] = [],
        max_requests: int = 0, 
        delay_constant: int = 0, 
        *args, 
        **kwargs
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
        generator: Generator | None = generator(
            *args,
            **kwargs
        ) if isinstance(generator, GeneratorClass) else generator
        
        if generator is None:
            raise ValueError(f"Generator not defined for local agent {self.__name__}")

        self._completor = Completor(generator,
            structures=list(map(to_prompt_structure, structures)),
            schemas=schemas,
            tools=tools,
            hooks=hooks,
            validators=validators, 
            interceptors=interceptors,
            delay_constant=delay_constant, 
            max_requests=max_requests, 
        )
        self._name = name
        self._description = description
        self._prompt_structure = to_prompt_structure(prompt_structure)
        super().__init__(*args, **kwargs)


    async def invoke(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._completor.execute(self._name, self._description, self._prompt_structure, args)


T = TypeVar("T", bound=Agent)
def agent(
        cls: type[T] | None = None, /, *,
        name: str | None = None,
        description: str | None = None,
        prompt_structure: PromptStructure | dict | list | str, 
        structures: list[PromptStructure | dict | list | str] = [],
        schemas: list[Schema] = [],
        tools: list[Tool] = [], 
        hooks: list[Hook] = [],
        validators: list[Validator] = [],
        max_requests: int = 0, 
        delay_constant: int = 0
    ):
    def decorator(cls: type[T]) -> type[T]:
            
        if not issubclass(cls, Agent):
            raise TypeError("agent decorator can only be used with subclass of Agent")

        src_file = inspect.getsourcefile(cls)
        _, src_line = inspect.getsourcelines(cls)

        def modify_path(structure_path: str):
            _structure_path = urlparse(structure_path)
            if _structure_path.scheme and _structure_path.scheme not in ("", "file"):
                ...
                # TODO: support remote files
            else:
                # Convert relative path to absolute path
                path = Path(_structure_path.path)
                if not path.is_absolute() and not path.is_file():
                    path = (Path(src_file).parent / path)
                    _structure_path = str(path)
                return _structure_path
            
        _prompt_structure = prompt_structure
        if isinstance(_prompt_structure, str):
            _prompt_structure = modify_path(_prompt_structure)

        _structures = []
        for structure in structures:
            if isinstance(structure, str):
                _structures.append(modify_path(structure))
            else:
                _structures.append(structure)

        class AgentWrapper(LocalAgentMixin, cls):
            def __init__(self, generator: GeneratorClass | Generator, interceptors: list[Interceptor] = [], *args, **kwargs):
                try:
                    super().__init__(
                        name=name, 
                        description=description, 
                        generator=generator, 
                        prompt_structure=_prompt_structure,
                        structures=_structures,
                        schemas=schemas,
                        tools=tools,
                        hooks=hooks,
                        validators=validators,
                        interceptors=interceptors,
                        max_requests=max_requests,
                        delay_constant=delay_constant,
                        *args,
                        **kwargs
                    )                
                except FileNotFoundError as e:
                    e.add_note(f'File "{Path(src_file)}", line {src_line}, in {cls.__qualname__}')
                    raise 
                
        AgentWrapper.__name__ = cls.__name__
        AgentWrapper.__qualname__ = cls.__qualname__
        return AgentWrapper
    
    if cls:
        return decorator(cls)
    return decorator






