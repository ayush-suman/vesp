from abc import abstractmethod
import asyncio
from enum import Enum
from typing import Any, Awaitable, Callable, Generic, Literal, Self, TypeVar, TypedDict
from vespwood.errors import InvalidStateError
from vespwood._utils import invoke_funcs

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
    


class Run(Awaitable[dict[str, Any] | None]):
    def __init__(self, args: dict[str, Any], *, extras: dict[str, Any] = {}):
        self._on_restart_callbacks: list[Callable[[dict[str, Any]], None | Awaitable[None]]] = []
        self._on_pause_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]] = []
        self._on_resume_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]] = []
        self._on_cancel_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]] = []
        self._on_retry_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]] = []
        self._on_error_callbacks: list[Callable[[Exception, dict[str, Any], dict[str, Any]], None | Awaitable[None]]] = []
        self._on_complete_callbacks: list[Callable[[_T], None]] = []
        self._state: RunState = RunState.READY
        self._lock: asyncio.Lock = asyncio.Lock()
        self._initial_args = args
        self._stashed_args = args
        self._stashed_extras = extras
        self._future: asyncio.Future[dict[str, Any] | None] = asyncio.get_event_loop().create_future()
        self._task = asyncio.create_task(self.__run__())

    @property
    def stashed_data(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return self._stashed_args, self._stashed_extras

    async def __run__(self):
        try:
            self._state = RunState.RUNNING
            async for args, extras in self.run(self._stashed_args, extras=self._stashed_extras):
                self._stashed_args = args
                self._stashed_extras = extras
            self._future.set_result(self._stashed_args)
            print("run complete. invoking on complete callbacks")
            await invoke_funcs(self._on_complete_callbacks, self._stashed_args)
        except asyncio.CancelledError as e:
            paused = e.args[0] if e.args else False
            if paused:
                await invoke_funcs(self._on_pause_callbacks, self._stashed_args, self._stashed_extras)
                self._state = RunState.PAUSED
            else:
                self._future.set_result(None)
                await invoke_funcs(self._on_cancel_callbacks, self._stashed_args, self._stashed_extras)
                RunState.CANCELLED
        except Exception as e:
            print("Error", e)
            self._future.set_exception(e)
            await invoke_funcs(self._on_error_callbacks, e, self._stashed_args, self._stashed_extras)
            self._state = RunState.ERROR
    
    @abstractmethod
    def run(self, args: dict[str, Any], *, extras: dict[str, Any] = {}): ...

    @property
    def state(self) -> RunState:
        return self._state

    @staticmethod
    def _invoke_callbacks(callbacks: list[Callable], *args: tuple[Any]):
        asyncio.create_task(invoke_funcs(callbacks, *args))

    def force_update(self, state: RunState, result: dict[str, Any] | None = None, error: BaseException | None = None, extras: dict[str, Any] = {}):
        # TODO: Update
        ...

    def start(self):
        # TODO: Call relevant callback or start
        ...

    def pause(self) -> bool: 
        if self._state == RunState.CANCELLED: return False
        if self._state == RunState.PAUSED: return False
        if self._state == RunState.COMPLETED or self._state == RunState.ERROR: return False
        async def _pause():
            if self._state == RunState.PAUSED: return
            self._state = RunState.PAUSING
            async with self._lock:
                await self._task.cancel(True)
        asyncio.create_task(_pause())
        return True

    def cancel(self) -> bool:
        if self._state == RunState.CANCELLED: return False
        if self._state == RunState.COMPLETED or self._state == RunState.ERROR: return False
        async def _cancel():
            async with self._lock:
                if self._state == RunState.CANCELLED: return
                self._state = RunState.CANCELLING
                await self._task.cancel()
        asyncio.create_task(_cancel())
        return True

    def resume(self): 
        async def _resume():
            if self._state == RunState.CANCELLED or self._state == RunState.COMPLETED:
                raise InvalidStateError("Cancelled or completed run can not be resumed")
            if self._state == RunState.ERROR:
                raise InvalidStateError("Run stopped with error. Can not resume.")
            if self._state == RunState.RUNNING: return
            self._state = RunState.RESUMING
            async with self._lock:
                self._task = asyncio.create_task(self.__run__())
                Run._invoke_callbacks(self._on_resume_callbacks, self._stashed_args, self._stashed_extras) 
        asyncio.create_task(_resume())

    def retry(self):
        if self._state != RunState.ERROR:
            raise InvalidStateError("Only run with error can be retried")
        async def _retry():
            async with self._lock:
                self._future = asyncio.get_event_loop().create_future()
                self._task = asyncio.create_task(self.__run__())
                Run._invoke_callbacks(self._on_retry_callbacks, self._stashed_args, self._stashed_extras)
        asyncio.create_task(_retry())

    def add_on_restart_callback(self, on_restart_callback: Callable[[dict[str, Any]], None | Awaitable[None]]): 
        # TODO: Add restart
        self._on_restart_callbacks.append(on_restart_callback)

    def add_on_pause_callback(self, on_pause_callback: Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]):
        self._on_pause_callbacks.append(on_pause_callback)
        
    def add_on_resume_callback(self, on_resume_callback: Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]):
        self._on_resume_callbacks.append(on_resume_callback)

    def add_on_cancel_callback(self, on_cancel_callback: Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]):
        self._on_cancel_callbacks.append(on_cancel_callback)

    def add_on_error_callback(self, on_error_callback: Callable[[Exception, dict[str, Any], dict[str, Any]], None | Awaitable[None]]):
        self._on_error_callbacks.append(on_error_callback)

    def add_on_retry_callback(self, on_retry_callback: Callable[[dict[str, Any], dict[str, Any]], None | Awaitable[None]]):
        self._on_retry_callbacks.append(on_retry_callback)

    def add_on_complete_callback(self, on_complete_callback: Callable[[dict[str, Any]], None | Awaitable[None]]): 
        self._on_complete_callbacks.append(on_complete_callback)

    def __await__(self):
        return self._future.__await__()

    def paused(self) -> bool:
        return self._state == RunState.PAUSED
        
    def cancelled(self) -> bool:
        return self._state == RunState.CANCELLED
    
    def done(self) -> bool: 
        return self._state == RunState.COMPLETED or self._state == RunState.ERROR
    
    def result(self) -> dict[str, Any]:
        return self._future.result()
    
    def exception(self) -> BaseException | None:
        return self._future.exception()
