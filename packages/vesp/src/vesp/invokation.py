from __future__ import annotations
from abc import abstractmethod
import asyncio
import inspect
from typing import Any, Awaitable, Callable, Literal, TypeAlias, TypeVar, Generic, TypedDict
from vesp._utils import invoke_funcs
from vesp.errors import InvalidStateError
from vespwood.run import Run, RunRestoreData


_O = TypeVar("_O")
_N = TypeVar("_N")

class OutputRestoreData(TypedDict):
    id: str
    run: RunRestoreData
    state: Literal["RUN", "POST_RUN", "OUTPUT", "ERROR"]
    output: Any | None = None
    error: Exception | None = None
    next_invokation_ids: list[str] | None = None

class InvokationRestoreData(TypedDict):
    id: str
    args: tuple[Any]
    kwargs: dict[str, Any]
    state: Literal["YIELDING", "YIELD_COMPLETE", "OUTPUT_COMPLETE"]
    outputs_restore_data: list[OutputRestoreData]


PostRunCallback: TypeAlias = Callable[[dict[str, Any]], _O | Awaitable[_O]]
class OutputFuture(Awaitable[_O], Generic[_O]):
    def __init__(self, run: Run[dict[str, Any]]):
        self._id: str = "" # TODO:
        self._run: Run[dict[str, Any]] = run
        self._future: asyncio.Future[_O | None] = asyncio.get_event_loop().create_future()
        self._nexts: list[Invokation] = []
        self._on_output_callbacks: list[Callable[[_O], None]] = []
        async def on_complete(args: dict[str, Any]):
            try:
                result = self.post_run_processing(args)
                if inspect.isawaitable(result):
                    result = await result
                self.set_result(result)
                asyncio.create_task(invoke_funcs(self._on_output_callbacks, result))
            except Exception as e:
                self.set_exception(e)
        self._run.add_on_complete_callback(on_complete)

    @property
    def run(self) -> Run[dict[str, Any]]:
        return self._run

    def force_update(self, ):
        # TODO: ...
        ...

    def start(self): 
        # TODO: 
        ...

    @abstractmethod
    def post_run_processing(run_result: dict[str, Any]) -> _O | Awaitable[_O]:
        ...

    def add_on_output_callback(self, callback: Callable[[_O], None]):
        self._on_output_callbacks.append(callback)

    def paused(self) -> bool:
        return self._run.paused()
        
    def cancelled(self) -> bool:
        return self._run.cancelled()

    def done(self) -> bool:
        return self._run.done() and self._future.done()
        
    def result(self) -> _O: 
        return self._future.result()
    
    def exception(self) -> BaseException | None:
        return self._future.exception()

    def add_next(self, invokation: Invokation):
        self._nexts.append(invokation)

    def set_result(self, result: _O):
        self._future.set_result(result)

    def set_exception(self, exception: type | BaseException):
        self._future.set_exception(exception)

    def __await__(self):
        return self._future.__await__()

    def cancel(self, msg: Any | None = None) -> bool:
        self._future.set_result(None)
        return self._run.cancel(msg)

    def pause(self, msg: Any | None = None) -> bool:
        self._future.set_result(None)
        return self._run.pause(msg)

    def resume(self):
        if self._future.done():
            self._future = asyncio.get_event_loop().create_future()
        self._run.resume()

    def retry(self):
        if self._run.done():
            if self._run.exception():
                return self._run.retry()
            if not self.exception():
                if self.done():
                    raise InvalidStateError("FutureOutput already completed. Can not retry")
                raise InvalidStateError("FutureOutput is running. Can not retry")
        return self._run.retry()


    def restart(self):
        ...


class Invokation(Generic[_O]):
    def __init__(self, args: tuple, kwargs: dict[str, Any]):
        self._id: str = "" # TODO:
        self._outputs: list[OutputFuture[_O]] = []
        self._args = args
        self._kwargs = kwargs
        self._future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._completion_promised: bool = False
        self._nexts: list[Invokation] = []
        self._on_complete_promise_callbacks: list[Callable[[], None]] = []
        self._on_complete_callbacks: list[Callable[[list[_O]], None]] = []
        self._on_output_promise_callbacks: list[Callable[[OutputFuture[_O]], None]] = []
        self._on_output_callbacks: list[Callable[[_O], None]] = []
        self._combined_future: asyncio.Future[list[_O]] = asyncio.Future()

    def promise_output(self, output: OutputFuture[_O]):
        if self._completion_promised:
            raise InvalidStateError("Can not promise new output once completion promised")
        for callback in self._on_output_callbacks:
            output.add_on_output_callback(callback)
        asyncio.create_task(invoke_funcs(self._on_output_promise_callbacks, output))

    def promise_complete(self):
        if self._completion_promised:
            raise ValueError("Completion already promised")
        self._completion_promised = True
        combined_awaitable = asyncio.create_task(asyncio.gather(*self._outputs))
        combined_awaitable.add_done_callback(lambda t: invoke_funcs(self._on_complete_callbacks, t.result()))
        combined_awaitable.add_done_callback(lambda t: self._combined_future.set_result(t.result()))

    def pause(self, msg: Any | None) -> bool:
        result = False
        for output in self._outputs:
            result |= output.pause(msg)
        return result

    def cancel(self, msg: Any | None) -> bool:
        result = False
        for output in self._outputs:
            result |= output.pause(msg)
        return result

    def resume(self) -> bool:
        for output in self._outputs:
            output.resume()

    def add_next(self, invokation: Invokation):
        self._nexts.append(invokation)

    def add_on_complete_promise_callback(self, callback: Callable[[], None]):
        self._on_complete_promise_callbacks.append(callback)

    def add_on_complete_callback(self, callback: Callable[[list[_O]], None]):
        self._on_complete_callbacks.append(callback)

    def add_on_output_promise_callback(self, callback: Callable[[OutputFuture[_O], None]]):
        self._on_output_promise_callbacks.append(callback)

    def add_on_output_callback(self, callback: Callable[[_O], None]):
        for output in self._outputs:
            output.add_on_output_callback(callback)

    def __await__(self):
        return self._combined_future.__await__()


