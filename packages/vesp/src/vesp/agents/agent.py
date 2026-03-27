import asyncio
from pathlib import Path
from typing import AsyncIterator, Callable, Concatenate, Literal, Any
from abc import ABCMeta, abstractmethod
from vesp.invokation import Invokation
from vespwood import (
    FormatKeys,
    Generator,
    GeneratorClass,
    Interceptor,
    Schema,
    Hook,
    PreparedArgs, 
    TaggedMessages, 
    Completor,
    Validator,
    Schematic
)
import inspect


class AgentMeta(ABCMeta):
    def __sub__(cls, other: Literal["public", "private"]) -> "AgentMeta":
        class ScopedAgent(cls):
            _accessibility = other

        ScopedAgent.__class__.__name__ = cls.__name__
        ScopedAgent.__class__.__qualname__ = cls.__qualname__
        return ScopedAgent

        

class BaseAgent(Schematic, metaclass=AgentMeta):  
    _accessibility = "private"

    def __sub__(self, other: Literal["public", "private"]) -> "BaseAgent":
        self._accessibility = other
        return self


    @property
    def is_public(self):
        return self._accessibility == "public"


    @abstractmethod
    def __call__(self, *args, **kwargs) -> Invokation:
        pass


class Agent[O](BaseAgent, metaclass=AgentMeta):
    def __init__(self, *args, **kwargs):
        self._name = self.__class__.__name__
        self._description = self.__doc__
        self._schema = Schematic.to_json_schema(self)
        super().__init__()

    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description

    @property
    def schema(self) -> dict[str, Any]:
        return self._schema
    

    @abstractmethod
    async def invoke(self, args: PreparedArgs) -> tuple[TaggedMessages, FormatKeys]:
        '''Accepts args_list, and adds outputs to the Invokation chain object'''
        ...


    @abstractmethod
    async def handle_responses(self, messages: TaggedMessages, format_keys: FormatKeys) -> O:
        ...


    def __get_output__(self, messages: TaggedMessages, format_keys: FormatKeys, *, future: asyncio.Future | None = None, chain: Invokation[O] | None = None) -> O:
        def on_output(output: O):
            if chain: chain.add_output(output)
            if future: future.set_result(output)
        # Step 3: Handle Response
        handle_response_task = asyncio.create_task(self.handle_responses(messages, format_keys))
        handle_response_task.add_done_callback(lambda t: on_output(t.result()))
        

    def __call__(self,  args: PreparedArgs) -> Invokation[O]:
        chain = Invokation()
        async def run_with() -> O:
            result = await self.invoke(args)
            return await self.__get_output__(*result, chain=chain)
        task = asyncio.create_task(run_with())
        task.add_done_callback(lambda _: chain.mark_completed())
        return chain
    

def agent[T: Agent](
        cls: type[T] | None = None, /, *,
        generator: GeneratorClass | Generator | None, 
        prompt_structure: str | None = None, 
        max_requests: int = 0, 
        delay_constant: int = 0, 
        schemas: list[Schema] = [],
        validators: list[Validator] = [], 
        tools: list[Invokable] = [], 
        hooks: list[Hook] = []):
    def decorator(cls: type[T]) -> type[T]:
        if not issubclass(cls, Agent):
            raise TypeError("agent decorator can only be used with subclass of Agent")
    
        class AgentWrapper(cls):
            def __init__(self, interceptors: list[Interceptor] = [], *args, **kwargs):
                _generator: Generator = generator(
                    *args,
                    **kwargs
                ) if isinstance(generator, GeneratorClass) else generator
                src_file = inspect.getsourcefile(cls)
                _, src_line = inspect.getsourcelines(cls)
                _prompt_structure = prompt_structure
                if isinstance(prompt_structure, str):
                    # Convert relative path to absolute path
                    path = Path(prompt_structure)
                    if not path.is_absolute() and not path.is_file():
                        path = (Path(src_file).parent / path)
                        _prompt_structure = str(path)
                try:
                    self.__completer = Completor(_generator,
                        prompt_structure=_prompt_structure, 
                        validators=validators, 
                        delay_constant=delay_constant, 
                        max_requests=max_requests, 
                        schemas=schemas,
                        tools=tools,
                        hooks=hooks,
                        interceptors=interceptors
                    )
                except FileNotFoundError as e:
                    e.add_note(f'File "{Path(src_file)}", line {src_line}, in {cls.__qualname__}')
                    raise 

                super().__init__(*args, **kwargs)
                if self.__completer.name != "":
                    self._name = self.__completer.name
                if self.__completer.description is not None and self.__completer.description != "":
                    self.description = self.__completer.description


            async def invoke(self, args: PreparedArgs) -> tuple[TaggedMessages, FormatKeys]:
                return await self.__completer(args)


            def __str__(self):
                return cls.__name__


            def __repr__(self):
                return cls.__name__
            
        AgentWrapper.__name__ = cls.__name__
        AgentWrapper.__qualname__ = cls.__qualname__
        return AgentWrapper
    
    if cls:
        return decorator(cls)
    else:
        return decorator


def returns_args[**I, O](func: Callable[Concatenate[Agent[O], I], PreparedArgs]) -> Callable[Concatenate[Agent[O], I], Invokation[O]]:
    def fn(self: Agent[O], *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        chain = Invokation()
        async def run_with():
            completion_futures: list[asyncio.Future] = []
            # Step 1: Prepare Args
            prepared_args_list = await func(self, *args, **kwargs)
            for prepared_args in prepared_args_list:
                #Step 2: Invoke
                future = asyncio.Future()
                completion_futures.append(future)
                invokation_task = asyncio.create_task(self.invoke(prepared_args))
                # Step 3: Handle Response
                invokation_task.add_done_callback(lambda t: self.__get_output__(*t.result(), future=future, chain=chain))
            return await asyncio.gather(*completion_futures)
        task = asyncio.create_task(run_with())
        task.add_done_callback(lambda _: chain.mark_completed())
        return chain
    return fn


def yields_args[**I, O](func: Callable[Concatenate[Agent[O], I], AsyncIterator[PreparedArgs]]) -> Callable[Concatenate[Agent[O], I], Invokation[O]]:
    def fn(self: Agent[O], *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        chain = Invokation()
        async def run_with():
            completion_futures: list[asyncio.Future] = []
            # Step 1: Prepare Args
            async for prepared_args in func(self, *args, **kwargs):
                #Step 2: Invoke
                future = asyncio.Future()
                completion_futures.append(future)
                invokation_task = asyncio.create_task(self.invoke(prepared_args))
                # Step 3: Handle Response
                invokation_task.add_done_callback(lambda t: self.__get_output__(*t.result(), future=future, chain=chain))
            return await asyncio.gather(*completion_futures)
        task = asyncio.create_task(run_with())
        task.add_done_callback(lambda _: chain.mark_completed())
        return chain
    return fn