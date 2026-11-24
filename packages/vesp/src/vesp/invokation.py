from __future__ import annotations
from abc import abstractmethod
import asyncio
import inspect
from typing import Any, Awaitable, Callable, Literal, TypeAlias, TypeVar, Generic, TypedDict
from vesp._utils.invoke_funcs import invoke_funcs
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
# class OutputFuture(Awaitable[_O], Generic[_O]):
#     def __init__(self, run: Run, post_run_callback: PostRunCallback):
#         self._id: str = "" # TODO:
#         self._run: Run = run
#         self._future: asyncio.Future[_O | None] = asyncio.get_event_loop().create_future()
#         self._nexts: list[Invokation] = []
#         self._on_pause_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
#         self._on_resume_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
#         self._on_cancel_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
#         self._on_retry_callbacks: list[Callable[[dict[str, Any], dict[str, Any]], None]] = []
#         self._on_error_callbacks: list[Callable[[Exception, dict[str, Any], dict[str, Any]], None]] = []
#         self._on_output_callbacks: list[Callable[[_O], None]] = []
#         async def on_complete(args: dict[str, Any]):
#             try:
#                 result = post_run_callback(args) 
#                 if inspect.isawaitable(result):
#                     result = await result
#                 self._future.set_result(result)
#                 asyncio.create_task(invoke_funcs(self._on_output_callbacks, result))
#             except Exception as e:
#                 self._future.set_exception(e)
#                 asyncio.create_task(invoke_funcs(self._on_error_callbacks, e, *run.stashed_data))
#         self._run.add_on_complete_callback(on_complete)

#         async def on_error(e: Exception, *a):
#             print("Setting exception to output", e)
#             self._future.set_exception(e)
#             asyncio.create_task(invoke_funcs(self._on_error_callbacks, e, *run.stashed_data))
#         self._run.add_on_error_callback(on_error)

#     @property
#     def run(self) -> Run:
#         return self._run

#     def force_update(self, ):
#         # TODO: ...
#         ...

#     def start(self): 
#         # TODO: 
#         ...

#     def add_on_pause_callback(self, callback: Callable[[dict[str, Any], dict[str, Any]], None]):
#         self._on_pause_callbacks.append(callback)

#     def add_on_resume_callback(self, callback: Callable[[dict[str, Any], dict[str, Any]], None]):
#         self._on_resume_callbacks.append(callback)

#     def add_on_retry_callback(self, callback: Callable[[dict[str, Any], dict[str, Any]], None]):
#         self._on_retry_callbacks.append(callback)

#     def add_on_cancel_callback(self, callback: Callable[[dict[str, Any], dict[str, Any]], None]):
#         self._on_cancel_callbacks.append(callback)

#     def add_on_error_callback(self, callback: Callable[[Exception, dict[str, Any], dict[str, Any]], None]):
#         self._on_error_callbacks.append(callback)

#     def add_on_output_callback(self, callback: Callable[[_O], None]):
#         self._on_output_callbacks.append(callback)

#     def add_output(self, output: _O):
#         self._future.set_result(output)
#         invoke_funcs(self._on)

#     def set_exception(self, exception: Exception):
#         self._future.set_exception(exception)

#     def paused(self) -> bool:
#         return self._run.paused()
        
#     def cancelled(self) -> bool:
#         return self._run.cancelled()

#     def done(self) -> bool:
#         return self._run.done() and self._future.done()
        
#     def result(self) -> _O: 
#         return self._future.result()
    
#     def exception(self) -> BaseException | None:
#         return self._future.exception()

#     def add_next(self, invokation: Invokation):
#         self._nexts.append(invokation)

#     def __await__(self):
#         return self._future.__await__()

#     def cancel(self, msg: Any | None = None) -> bool:
#         self._future.set_result(None)
#         return self._run.cancel(msg)

#     def pause(self, msg: Any | None = None) -> bool:
#         self._future.set_result(None)
#         return self._run.pause(msg)

#     def resume(self):
#         if self._future.done():
#             self._future = asyncio.get_event_loop().create_future()
#         self._run.resume()

#     def retry(self):
#         if self._run.done():
#             if self._run.exception():
#                 return self._run.retry()
#             if not self.exception():
#                 if self.done():
#                     raise InvalidStateError("FutureOutput already completed. Can not retry")
#                 raise InvalidStateError("FutureOutput is running. Can not retry")
#         return self._run.retry()


#     def restart(self):
#         ...


class Invokation(Awaitable[list[_O | None]], Generic[_O]):
    def __init__(self, args: tuple, kwargs: dict[str, Any], post_run_callback: PostRunCallback):
        self._id: str = "" # TODO:
        self._runs: list[Run] = []
        self._outputs: list[asyncio.Future[_O]] = []
        self._args = args
        self._kwargs = kwargs
        self._future: asyncio.Future = asyncio.get_event_loop().create_future()
        
        self._completion_promised: bool = False

        self._on_output_promise_callbacks: list[Callable[[Awaitable[_O]], None]] = []
        self._on_output_callbacks: list[Callable[[_O], None]] = []
        self._on_complete_promise_callbacks: list[Callable[[], None]] = []
        self._on_complete_callbacks: list[Callable[[list[_O]], None]] = []

        self._combined_future: asyncio.Future[list[_O]] = asyncio.Future()
        self._post_run_callback = post_run_callback

    def promise_output(self, run: Run):
        if self._completion_promised:
            raise InvalidStateError("Can not promise new output once completion promised")
        self._runs.append(run)
        output_future = asyncio.get_event_loop().create_future()
        self._outputs.append(output_future)
        async def on_run_complete(args: dict[str, Any] | None):
            if args is None: output_future.set_result(None)
            try:
                result = self._post_run_callback(args)
                if inspect.isawaitable(result):
                    result = await result
                output_future.set_result(result)
                await invoke_funcs(self._on_output_callbacks, result)
            except Exception as e:
                output_future.set_exception(e)
        run.add_on_complete_callback(on_run_complete)
        async def on_run_error(e, *_):
            output_future.set_exception(e)
        run.add_on_error_callback(on_run_error)
        asyncio.create_task(invoke_funcs(self._on_output_promise_callbacks, output_future))

    def promise_complete(self):
        if self._completion_promised:
            raise InvalidStateError("Completion already promised")
        self._completion_promised = True
        async def schedule_callback():
            try:
                outputs = await asyncio.gather(*self._outputs)
                await invoke_funcs(self._on_complete_callbacks, outputs)
                self._combined_future.set_result(outputs)
            except Exception as e:
                self._combined_future.set_exception(e)
        asyncio.create_task(schedule_callback())

    def pause(self) -> bool:
        result = False
        for run in self._runs:
            result |= run.pause()
        return result

    def cancel(self) -> bool:
        result = False
        for run in self._runs:
            result |= run.cancel()
        return result

    def resume(self) -> bool:
        for run in self._runs:
            if run.paused(): run.resume()
        
    def add_on_complete_promise_callback(self, callback: Callable[[], None]):
        self._on_complete_promise_callbacks.append(callback)

    def add_on_complete_callback(self, callback: Callable[[list[_O]], None]):
        self._on_complete_callbacks.append(callback)

    def add_on_output_promise_callback(self, callback: Callable[[Awaitable[_O], None]]):
        self._on_output_promise_callbacks.append(callback)

    def add_on_output_callback(self, callback: Callable[[_O], None]):
        self._on_output_callbacks.append(callback)

    def __await__(self):
        return self._combined_future.__await__()


