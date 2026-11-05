
import inspect
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar, Protocol, cast
from urllib.parse import urlparse
import uuid

from vesp.agents.agent.agent import AgentLike, Agent
from vesp.invokation import Invokation
from vespwood import (
    Generator, Interceptor, 
    PromptStructure, Executor, AsyncExecutor, 
    Schema, Tool, Hook, Validator
)


A = ParamSpec("A")
P = ParamSpec("P")
O = TypeVar("O")

class LocalAgentLike(Protocol[P, O]):
    def __call__(self, generator_factory: Callable[[], Generator], interceptors: list[Interceptor], *args: P.args, **kwargs: P.kwargs) -> Invokation[O]: 
        ...


def agent(
    prompt_structure: PromptStructure | dict | list | str,
    executor: type[Executor] = AsyncExecutor,
    name: str | None = None,
    description: str | None = None,
    structures: list[PromptStructure | dict | list | str] = [],
    schemas: list[Schema] = [],
    tools: list[Tool] = [], 
    hooks: list[Hook] = [],
    validators: list[Validator] = [],
    max_requests: int = 0, 
    delay_constant: float = 0,
    **executor_args
):
    def decorator(cls: Callable[A, AgentLike[P, O]]) -> Callable[A, LocalAgentLike[P, O]]:
        base = cast(type[Agent], cls)

        src_file = inspect.getsourcefile(base)
        _, src_line = inspect.getsourcelines(base)

        def modify_path(structure_path: str):
            _structure_path = urlparse(structure_path)
            if _structure_path.scheme and _structure_path.scheme in ("http", "https"):
                import requests
                response = requests.get(structure_path)
                response.raise_for_status()
                file_content = response.text
                try:
                    import json
                    _structure_path = json.loads(file_content)
                except:
                    try:
                        import yaml # type: ignore
                        _structure_path = yaml.safe_load(file_content)
                    except:
                        raise ValueError("The content of the given url", structure_path, "can not be parsed into PromptStructure")
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

        def to_prompt_structure(structure: PromptStructure | dict | list | str) -> PromptStructure:
            if isinstance(structure, PromptStructure):
                return structure
            elif isinstance(structure, str):
                return PromptStructure.load_from_file(uuid.uuid4(), structure)
            elif isinstance(structure, dict):
                return PromptStructure.load_from_dict(uuid.uuid4(), structure)
            elif isinstance(structure, list):
                id = uuid.uuid4()
                return PromptStructure.load_from_list(
                    id,
                    structure,
                    name=id.hex,
                )

        _executor = executor(
            structures=list(map(to_prompt_structure, structures)),
            schemas=schemas,
            tools=tools,
            hooks=hooks,
            validators=validators,
            delay_constant=delay_constant, 
            max_requests=max_requests, 
            **executor_args
        )
        class AgentWrapper(base):
            def __init__(self, *args, **kwargs):
                self._name = name or base.__name__
                self._description = description or base.__doc__ or ""
                self._prompt_structure = to_prompt_structure(prompt_structure)
                self._executor = _executor
                cls.__init__(self, *args, **kwargs)
                Agent.__init__(self, name, description)

            def invoke(self, prepared_args: dict[str, Any], generator_factory: Callable[[], Generator], interceptors: list[Interceptor], *args: P.args, **kwargs: P.kwargs) -> dict[str, Any]:
                return self._executor.execute(self._name, self._description, self._prompt_structure, prepared_args, generator_factory, interceptors=interceptors)

                
            # def __call__(self, generator_factory: GeneratorClass | Callable[[], Generator], interceptors: list[Interceptor], *args: P_local.args, **kwargs: P_local.kwargs) -> Invokation[O_local]:
            #     if generator_factory is None:
            #         raise ValueError(f"Generator not defined for local agent {self.__name__}")

            #     call = super().__call__
            #     if inspect.isgeneratorfunction(call): ...
            #     elif inspect.isasyncgenfunction(call): ...
            #     elif inspect.iscoroutinefunction(call): ...
            #     else:
            #         input_args = call(*args, **kwargs)
            #         chain = Invokation()
            #         async def run_with() -> O:
            #             run = _executor.execute(self._name, self._description, self._prompt_structure, input_args, generator_factory, interceptors=interceptors)
            #             async def get_output(output):
            #                 return await self.__get_output__(output, chain=chain)
            #             run.on_complete(get_output)
            #         task = asyncio.create_task(run_with())
            #         task.add_done_callback(lambda _: chain.mark_completed())
            #         return chain
            
        
        AgentWrapper.__name__ = base.__name__
        AgentWrapper.__qualname__ = base.__qualname__
        AgentWrapper.__module__ = base.__module__
        return AgentWrapper
    
    return decorator

# @agent("")
# class TestAgent(Agent):
#     def prepare_args(self, application_id: int, subapp_id: int, utkarsh: str): 
#         ...

#     def handle_responses(self, **kwargs) -> bool:
#         return super().handle_responses(**kwargs)


# a = TestAgent()
# invokation = a(lambda role: JevGenerator() if role =="choices" else OpenAIGenerator(), [], )