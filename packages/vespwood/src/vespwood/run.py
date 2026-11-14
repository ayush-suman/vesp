from abc import abstractmethod
import asyncio
from enum import Enum
from typing import Any, Awaitable, Callable, Generic, Literal, Self, TypeVar, TypedDict
from vespwood.errors import InvalidStateError
from vespwood._utils import invoke_funcs

_T = TypeVar("_T")

class RunRestoreData(TypedDict):
    id: str
    args: dict[str, Any]
    extras: dict[str, Any]
    state: Literal["RUNNING", "PAUSING", "PAUSED", "RESUMING", "ERROR", "RESTARTING", "CANCELLING", "CANCELLED", "COMPLETED"]
    result: dict[str, Any] | None = None
    error: Exception | None = None


class RunState(Enum):
    READY = 0
    RUNNING = 1
    PAUSING = 2
    PAUSED = 3
    RESUMING = 4
    ERROR = 5
    RESTARTING = 6
    CANCELLING = 7
    CANCELLED = 8
    COMPLETED = 9
    


class Run(Awaitable[_T | None], Generic[_T]):
    def __init__(self, args: dict[str, Any], *, extras: dict[str, Any] = {}):
        self._on_restart_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._on_pause_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
        self._on_resume_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
        self._on_cancel_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
        self._on_retry_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
        self._on_error_callbacks: list[Callable[[Exception, dict[str, Any], dict[str, Any]], None]] = []
        self._on_complete_callbacks: list[Callable[[_T], None]] = []
        self._state: RunState = RunState.READY
        self._lock: asyncio.Lock = asyncio.Lock()
        self._stashed_args = args
        self._stashed_extras = extras
        self._future: asyncio.Future[_T | None] = asyncio.get_event_loop().create_future()
        self.__run__(args, extras=extras)
    
    @abstractmethod
    def __run__(self, args: dict[str, Any], *, extras: dict[str, Any] = {}): ...
    
    @abstractmethod
    async def __halt__(self, msg: Any | None) -> tuple[dict[str, Any], dict[str, Any]]: ...

    @property
    def state(self) -> RunState:
        return self._state

    @staticmethod
    def _invoke_callbacks(callbacks: list[Callable], *args: tuple[Any]):
        asyncio.create_task(invoke_funcs(callbacks, *args))

    def force_update(self, state: RunState, result: _T | None = None, error: BaseException | None = None, extras: dict[str, Any] = {}):
        # TODO: Update
        ...

    def start(self):
        # TODO: Call relevant callback or start
        ...

    def pause(self, msg: Any | None = None) -> bool: 
        if self._state == RunState.CANCELLED: return False
        if self._state == RunState.PAUSED: return False
        if self._state == RunState.COMPLETED or self._state == RunState.ERROR: return False
        async def _pause():
            if self._state == RunState.PAUSED: return
            self._state = RunState.PAUSING
            async with self._lock:
                stashed_args, stashed_extras = await self.__halt__(msg)
                self._future.set_result(None)
                Run._invoke_callbacks(self._on_pause_callbacks, stashed_args, stashed_extras)
                self._stashed_args = stashed_args
                self._stashed_extras = stashed_extras
                self._state = RunState.PAUSED
        asyncio.create_task(_pause())
        return True

    def resume(self): 
        async def _resume():
            if self._state == RunState.CANCELLED:
                raise InvalidStateError("Cancelled run can not be resumed")
            if self._state == RunState.ERROR:
                raise InvalidStateError("Run stopped with error. Can not resume.")
            if self._state == RunState.RUNNING: return
            self._state = RunState.RESUMING
            async with self._lock:
                self.__run__(self._stashed_args, extras=self._stashed_extras)
                self._future = asyncio.get_event_loop().create_future()
                Run._invoke_callbacks(self._on_resume_callbacks, self._stashed_args, self._stashed_extras)
                self._state = RunState.RUNNING
        asyncio.create_task(_resume())

    def retry(self):
        if self._state != RunState.ERROR or self._state != RunState.CANCELLED:
            raise InvalidStateError("Only runs that are cancelled or has stopped due to error can be retried")
        async def _retry():
            async with self._lock:
                if not hasattr(self, "_stashed_args") or not hasattr(self, "_stashed_extras"):
                    raise InvalidStateError("Unable retry due to missing args or extras")
                self.__run__(self._stashed_args, extras=self._stashed_extras)
                self._future = asyncio.get_event_loop().create_future()
                Run._invoke_callbacks(self._on_retry_callbacks, self._stashed_args, self._stashed_extras)
                self._state = RunState.RUNNING
            asyncio.create_task(_retry())

    def restart(self):
        async def _restart():
            async with self._lock:
                if self._state != RunState.CANCELLED or self._state != RunState.ERROR:
                    self._stashed_args, _ = await self.__halt__()
                self._state = RunState.RESTARTING
                self.__run__(self._stashed_args)
                self._future = asyncio.get_event_loop().create_future()
                Run._invoke_callbacks(self._on_restart_callbacks, self._stashed_args)
                self._state = RunState.RUNNING
        asyncio.create_task(_restart())

    def cancel(self, msg: Any | None = None) -> bool:
        if self._state == RunState.CANCELLED: return False
        if self._state == RunState.COMPLETED or self._state == RunState.ERROR: return False
        async def _cancel():
            async with self._lock:
                if self._state == RunState.CANCELLED: return
                self._state = RunState.CANCELLING
                stashed_args, stashed_extras = await self.__halt__(msg)
                self._future.set_result(None)
                Run._invoke_callbacks(self._on_cancel_callbacks, stashed_args, stashed_extras)
                self._stashed_args = stashed_args
                self._stashed_extras = stashed_extras
                self._state = RunState.CANCELLED
        asyncio.create_task(_cancel())
        return True

    def set_result(self, value: _T): 
        if self._state == RunState.CANCELLED:
            raise InvalidStateError("Can not add result to cancelled Run")
        if self._state == RunState.ERROR:
            raise InvalidStateError("Run stopped with error. Can not add result")
        self._state = RunState.COMPLETED
        self._future.set_result(value)
        Run._invoke_callbacks(self._on_complete_callbacks, value)
        

    def set_exception(self, exception: type | BaseException, stashed_args: dict[str, Any] | None = None, stashed_extras: dict[str, Any] | None = None):
        if self._state == RunState.COMPLETED:
            raise InvalidStateError("Run is already completed. Can not add error")
        if self._state == RunState.PAUSED:
            raise InvalidStateError("Can not add error while the run is paused")
        if self._state == RunState.CANCELLED:
            raise InvalidStateError("Run is already cancelled. Can not add error")
        self._state = RunState.ERROR
        self._future.set_exception(exception)
        if stashed_args: self._stashed_args = stashed_args
        if stashed_extras: self._stashed_extras = stashed_extras
        Run._invoke_callbacks(self._on_error_callbacks, exception, stashed_args, stashed_extras)
        

    def add_on_restart_callback(self, on_restart_callback: Callable[[dict[str, Any]], None]): 
        self._on_restart_callbacks.append(on_restart_callback)

    def add_on_pause_callback(self, on_pause_callback: Callable[[dict[str, Any], dict[str, Any]], None]):
        self._on_pause_callbacks.append(on_pause_callback)
        
    def add_on_resume_callback(self, on_resume_callback: Callable[[dict[str, Any], dict[str, Any]], None]):
        self._on_resume_callbacks.append(on_resume_callback)

    def add_on_cancel_callback(self, on_cancel_callback: Callable[[dict[str, Any], dict[str, Any]], None]):
        self._on_cancel_callbacks.append(on_cancel_callback)

    def add_on_error_callback(self, on_error_callback: Callable[[Exception, dict[str, Any], dict[str, Any]], None]):
        self._on_error_callbacks.append(on_error_callback)

    def add_on_complete_callback(self, on_complete_callback: Callable[[_T], None]): 
        self._on_complete_callbacks.append(on_complete_callback)

    def __await__(self):
        return self._future.__await__()

    def paused(self) -> bool:
        return self._state == RunState.PAUSED
        
    def cancelled(self) -> bool:
        return self._state == RunState.CANCELLED
    
    def done(self) -> bool: 
        return self._state == RunState.COMPLETED or self._state == RunState.ERROR
    
    def result(self) -> _T:
        return self._future.result()
    
    def exception(self) -> BaseException | None:
        return self._future.exception()
