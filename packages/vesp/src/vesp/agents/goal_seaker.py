from abc import abstractmethod
from typing import Callable, Any

from vesp.visibility import Visibility
from vesp.invokation import Invokation
from .agent import BaseAgent
from .team import AgentsTeam, HandoverResponse
from vespwood import Completor, GeneratorClass, Generator


class GoalSeakerTeam(AgentsTeam):
    def __init__(self, generator: Callable[..., Completor], *args, **kwargs):
        self.__generator__: Completor = generator(*args, **kwargs)
        super().__init__(self.create_routes(), *args, **kwargs)

    @property
    def goal(self) -> str:
        return self.__doc__
    
    
    @abstractmethod
    def create_channels(self) -> dict[str, list[str]]:
        pass


    def handover(self, route: str, output: Any, chain: list[Invokation]) -> list[HandoverResponse] | None:
        pass



def goal_seaker_team[T: GoalSeakerTeam](cls: type[T] | None = None, /, *, entrypoint: str = "/", generator: GeneratorClass | Generator | None):
    def decorator(cls: type[T]) -> type[T]:
        # Assert class is GoalSeakerTeam subclass
        if not issubclass(cls, GoalSeakerTeam):
            raise TypeError("goal_seaker_team decorator can only be used with subclass of GoalSeakerTeam")
        
        # Actual decorator implementation
        class GoalSetterTeamWrapper(cls):
            def __init__(self, *args, **kwargs):
                self.__name__ = cls.__name__
                self.__doc__ = cls.__doc__
                super().__init__(generator, *args, **kwargs)
                if self.index:
                    self[entrypoint] = self.index - Visibility.PUBLIC


            @property
            def index(self) -> BaseAgent | None:
                return self.get(entrypoint)

        
        return GoalSetterTeamWrapper
    if cls:
        return decorator(cls)
    else:
        return decorator
