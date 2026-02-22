from asyncio import Protocol


class Caller[T](Protocol):
    def __getitem__(self, name: str) -> T:
        return self.__call__(name)
    
    
    def __call__(self, name: str) -> T:
        ...
