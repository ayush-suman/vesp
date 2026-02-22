import asyncio
from pathlib import Path
from typing import AsyncIterator, Literal, Any
from abc import ABCMeta, abstractmethod
from vesp.visibility import Visibility
from vespwood import (
    FormatKeys, 
    Generator, GeneratorClass, 
    Completor,
    Interceptor,
    Schema,
    Hook,
    Tool,
    Validator,
    Schematic,
    PreparedArgs,
    TaggedMessages,
    to_json_schema
)
import inspect
from vesp.invokation import Invokation


class AgentMeta(ABCMeta):
    def __sub__(cls, other: Visibility) -> "AgentMeta":
        class ScopedAgent(cls):
            _visibility: Visibility = other

        ScopedAgent.__class__.__name__ = cls.__name__
        ScopedAgent.__class__.__qualname__ = cls.__qualname__
        return ScopedAgent

        

class BaseAgent(Schematic, metaclass=AgentMeta):  
    _visibility: Visibility = Visibility.PRIVATE

    def __sub__(self, other: Visibility) -> "BaseAgent":
        self._visibility = other
        return self


    @property
    def is_public(self):
        return self._visibility == Visibility.PUBLIC


    @abstractmethod
    def __call__(self, *args, **kwargs) -> Invokation:
        pass


class Agent[**I, O](BaseAgent, metaclass=AgentMeta):
    def __init__(self, *args, **kwargs):
        self._name = self.__class__.__name__
        self._description = self.__doc__
        self._schema = to_json_schema(self.prepare_args)
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
    async def prepare_args(self, *args: I.args, **kwargs: I.kwargs) -> AsyncIterator[tuple[TaggedMessages, FormatKeys]]:
        ...


    @abstractmethod
    async def invoke(self, args: PreparedArgs) -> tuple[TaggedMessages, FormatKeys]:
        '''Accepts args_list, and adds outputs to the Invokation chain object'''
        ...


    @abstractmethod
    async def handle_responses(self, messages: TaggedMessages, format_keys: FormatKeys) -> O:
        ...


    def __on_invokation__(self, chain: Invokation[O], messages: TaggedMessages, format_keys: FormatKeys, future: asyncio.Future):
        def on_output(output: O):
            chain.add_output(output)
            
            future.set_result(None)
        # Step 3: Handle Response
        handle_response_task = asyncio.create_task(self.handle_responses(messages, format_keys))
        handle_response_task.add_done_callback(lambda t: on_output(t.result()))


    async def __run__(self, chain: Invokation[O], *args: I.args, **kwargs: I.kwargs) -> None:
        completion_futures: list[asyncio.Future] = []
        # Step 1: Prepare Args
        async for args in self.prepare_args(*args, **kwargs):
            #Step 2: Invoke
            future = asyncio.Future()
            completion_futures.append(future)
            invokation_task = asyncio.create_task(self.invoke(args))
            # Step 3: Handle Response
            invokation_task.add_done_callback(
                lambda t, future=future: self.__on_invokation__(chain, *t.result(), future)
            )
        await asyncio.gather(*completion_futures)
        chain.mark_completed()


    def __call__(self, *args: I.args, **kwargs: I.kwargs) -> Invokation[O]:
        chain = Invokation()
        asyncio.create_task(self.__run__(chain, *args, **kwargs))
        return chain
    


def agent[T: Agent](
        cls: type[T] | None = None, /, *,
        generator: GeneratorClass | Generator | None, 
        prompt_structure: str | None = None, 
        max_requests: int = 0, 
        delay_constant: int = 0, 
        schemas: list[Schema] = [],
        validators: list[Validator] = [], 
        tools: list[Tool] = [], 
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



