from abc import abstractmethod
import asyncio
from typing import List, Optional, Callable, Dict, Any, Tuple, TypeVar, Type
from vesp.invokation import Invokation, Output
from .agent import BaseAgent
from vesp.visibility import Visibility

type AgentLike = BaseAgent | Callable[..., BaseAgent]
type TeamLike = Dict[str, "TeamLike" | AgentLike]

type Next = str 
type Args = List[Any]
type Kwargs = Dict[str, Any]
type NextWithArgs = Tuple[Next, Args]
type NextWithKwargs = Tuple[Next, Kwargs]
type NextWithArgsAndKwargs = Tuple[Next, Args, Kwargs]

type HandoverResponse = Next | NextWithArgs | NextWithKwargs | NextWithArgsAndKwargs

def normalise(routes: TeamLike, prefix: str = "") -> Dict[str, BaseAgent]:
    normalised_dict = {}
    for key, value in routes.items():
        if isinstance(value, dict):
            normalised_dict.update(normalise(value, f"{prefix}/{key}"))
        else:
            normalised_dict.update({f"{prefix}/{key}": value})
    return normalised_dict


  
class Chain(list[Invokation]):
    def __init__(self, *invokation: List[Invokation]):
        super().__init__(invokation)

    def with_next(self, invokation: Invokation) -> "Chain":
        chain = Chain(self)
        chain.append(invokation)
        return chain


class AgentsTeam(dict, BaseAgent):
    def __init__(self, route_map: Dict[str, any], *args, **kwargs):
        for route, agent_class in route_map.items():
            route = route.removeprefix('/')
            paths = route.split('/')
            if isinstance(agent_class, dict):
                self.update({paths.pop(0): AgentsTeam({'/'.join(paths): agent_class} if len(paths) > 0 else agent_class, *args, **kwargs)})
            elif isinstance(agent_class, BaseAgent):
                self.update({paths.pop(0): agent_class})
            else:
                self.update({paths.pop(0): AgentsTeam({'/'.join(paths): agent_class}, *args, **kwargs) if len(paths) > 0 else agent_class(*args, **kwargs)})
        self.__args = args
        self.__kwargs = kwargs


    def normalise(self) -> Dict[str, BaseAgent]:
        return normalise(self)
            

    @abstractmethod
    def create_routes(self) -> Dict[str, any]:
        pass

    
    @property
    @abstractmethod
    def entrypoint(self) -> str:
        pass
    
    
    @property
    def index(self) -> BaseAgent:
        return self[self.entrypoint]


    def __getitem__(self, key: str) -> BaseAgent:
        if key.__contains__('/'):
            key = key.removeprefix('/')
            paths = key.split('/')
            agent = self
            for path in paths:
                agent = agent[path.strip()]
            if agent is None:
                raise ValueError(f"No agent found at {key} in team {self.name}")
            return agent
        else:
            agent = super().__getitem__(key)
            if agent is None:
                raise ValueError(f"No agent found at {key} in team {self.name}")
            return agent
        

    def __setitem__(self, key: str, value: TeamLike | AgentLike):
        key = key.removeprefix('/')
        paths = key.split('/')
        agent = self
        while len(paths) > 0:
            path = paths.pop(0)
            if len(paths) == 0:
                if isinstance(value, dict):
                    agent.update({path: AgentsTeam(value, *self.__args, **self.__kwargs)})                        
                elif isinstance(value, BaseAgent):
                    agent.update({path: value})
                else:
                    agent.update({path: value(*self.__args, **self.__kwargs)})
                return
            
            if not agent.get(path):
                if isinstance(value, dict):
                    agent.update({path: AgentsTeam({'/'.join(paths): value})})
                elif isinstance(value, BaseAgent):
                    agent.update({path: value})
                else:
                    agent.update({path: AgentsTeam({'/'.join(paths): value}, *self.__args, **self.__kwargs)})
                return

            agent = agent[path]
            


    def __contains__(self, key: str) -> bool:
        if key.__contains__('/'):
            key = key.removeprefix('/')
            paths = key.split('/')
            agent = self
            for path in paths:
                if not agent.get(path):
                    return False
                agent = agent[path]
            return True
        else:
            return super().__contains__(key)
        
    
    def get(self, key: str, default: Optional[BaseAgent] = None):
        if key in self:
            return self[key]
        return default
        
    
    def __add__(self, other: TeamLike) -> "AgentsTeam":
        other = normalise(other)
        for key, value in other.items():
            self[key] = value
        return self
    
        
    def __radd__(self, other: TeamLike) -> "AgentsTeam":
        other = normalise(other)
        for key, value in other.items():
            self[key] = value
        return self
    
    
    def __iadd__(self, other: TeamLike) -> "AgentsTeam":
        other = normalise(other)
        for key, value in other.items():
            self[key] = value
        return self


    @abstractmethod
    async def handover(self, route: str, output: Any, chain: list[Invokation]) -> Optional[List[HandoverResponse]]:
        pass


    async def __handover__(self, route: str, output: Output) -> None:
        handovers = await self.handover(route, output.data, output.chain)
        if handovers:
            for response in handovers:
                next_route, args, kwargs = response
                if isinstance(response, str):
                    next_route = response
                else:
                    if isinstance(response, (str, list)):
                        next_route, args = response
                    elif isinstance(response, (str, dict)):
                        next_route, kwargs = response
                    else:
                        next_route, args, kwargs = response
                agent = self[next_route]
                next: Invokation = agent(*args, **kwargs) @ route
                output.add_next(next)
                next.on_output(lambda o: asyncio.create_task(self.__handover__(next_route, o)))
        output.processed()
                

    def __call__(self, *args, **kwargs) -> Invokation:
        route = kwargs.get('route') or self.entrypoint
        agent = self[route]
        if agent.is_not_public:
            raise ValueError("Agent ", agent, "in team ", self.name, "cannot be invoked publicly")
        invokation = agent(*args, **kwargs) @ route
        invokation.on_output(lambda o: asyncio.create_task(self.__handover__(route, o)))
        wrapper = Invokation.wraps(invokation)
        return wrapper


    @property
    def name(self):
        return self.__name__


    @property
    def description(self) -> str:
        return self.__doc__ or ""


    @property
    def schema(self) -> Dict[str, Any]:
        routes = self.normalise()
        properties: dict[str, any] = self.index.schema["properties"]
        oneOf = [{
            "properties": properties,
            "required": [ *properties ],
            "additionalProperties": False
        }]
        for route, agent in routes.items():
            if agent.is_public:
                oneOf.append({
                    "properties": {
                        "route": { "const": route },
                        **agent.schema["properties"]
                    },
                    "required": ["route", *agent.schema["properties"]],
                    "additionalProperties": False
                })

        return {
             "type": "object",
             "properties": properties,
             "oneOf": oneOf
        }

T = TypeVar('T', bound=AgentsTeam)

def team(entrypoint: str = "/"):
    def decorator(cls: Type[T]):
        # Assert class is AgentsTeam subclass
        if not issubclass(cls, AgentsTeam):
            raise TypeError("team decorator can only be used with subclass of AgentsTeam")
        
        # Actual decorator implementation
        class TeamWrapper(cls):        
            def __init__(self, *args, **kwargs):
                self.__name__ = cls.__name__
                self.__doc__ = cls.__doc__
                super().__init__(self.create_routes(), *args, **kwargs)
                if self.index:
                    self[entrypoint] = self.index - Visibility.PUBLIC


            @property
            def entrypoint(self) -> str:
                return entrypoint

        return TeamWrapper
    return decorator


# Ideas: Other team types 
# - Simple State Machine uses provided list of routes to simply follow the list
