from typing import TypeVar, Protocol

T = TypeVar("T")


class Caller(Protocol[T]):
    def __getitem__(self, name: str) -> T:
        return self.__call__(name)
    
    
    def __call__(self, name: str) -> T:
        ...
