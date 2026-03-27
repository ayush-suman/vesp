from typing import Any, Callable, List, Optional, get_type_hints

from vesp.invokation import Invokation
from .agent import BaseAgent
from .team import HandoverResponse, TeamLike, AgentsTeam


def routes(entrypoint: str = "/"):
    def decorator(func: Callable[[], TeamLike]):
        # Assert correct function type
        hints = get_type_hints(func)
        return_type = hints.get('return', None)
        if return_type is not TeamLike:
            raise TypeError("decorated function should return a TeamLike dict")
        
        # Actual decorator implementation
        class TeamWrapper(AgentsTeam):
            def __init__(self, *args, **kwargs):
                self.__name__ = func.__name__
                self.__doc__ = func.__doc__
                super().__init__(self.create_routes(), *args, **kwargs)


            @property
            def index(self) -> Optional[BaseAgent]:
                return self.get(entrypoint)
            
            def create_routes(self) -> TeamLike:
                return func()
            
            
            def handover(self, route: str, output: Any, chain: list[Invokation]) -> Optional[List[HandoverResponse]]:
                return None
            
        return TeamWrapper
    return decorator