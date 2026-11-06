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
                result = self.set_post_run_callback(args)
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
    def set_post_run_callback(run_result: dict[str, Any]) -> _O | Awaitable[_O]:
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
        self._on_complete_callbacks: list[Callable[[], None]] = []
        self._on_output_promise_callbacks: list[Callable[[OutputFuture[_O]], None]] = []
        self._on_output_callbacks: list[Callable[[_O], None]] = []
        self._unresolved_output_count = 0

    def promise_output(self, output: OutputFuture[_O]):
        if self._completion_promised:
            raise InvalidStateError("Can not promise new output once completion promised")
        self._unresolved_output_count += 1
        def on_output():
            self._unresolved_output_count -= 1
            if self._unresolved_output_count == 0 and self._completion_promised:
                asyncio.create_task(invoke_funcs(self._on_complete_callbacks))
        output.add_on_output_callback(on_output)
        for callback in self._on_output_callbacks:
            output.add_on_output_callback(callback)
        asyncio.create_task(invoke_funcs(self._on_output_promise_callbacks, output))

    def promise_complete(self):
        if self._completion_promised:
            raise ValueError("Completion already promised")
        self._completion_promised = True
        if self._unresolved_output_count == 0:
            asyncio.create_task(invoke_funcs(self._on_complete_callbacks))
        

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

    def add_on_complete_callback(self, callback: Callable[[], None]):
        self._on_complete_callbacks.append(callback)

    def add_on_output_promise_callback(self, callback: Callable[[OutputFuture[_O], None]]):
        self._on_output_promise_callbacks.append(callback)

    def add_on_output_callback(self, callback: Callable[[_O], None]):
        for output in self._outputs:
            output.add_on_output_callback(callback)



# class AliveCountRef:
#     __slots__ = '_count', '_dropped_to_zero', '_on_zero_alive_callbacks'

#     def __init__(self, start: int = 0):
#         self._count: int = start
#         self._dropped_to_zero: bool = False
#         self._on_zero_alive_callbacks: list[Callable[[], None]] = []


#     @property
#     def count(self) -> int:
#         return self._count


#     @property
#     def dropped_to_zero(self) -> bool:
#         return self._dropped_to_zero


#     def increment(self):
#         if not self._dropped_to_zero:
#             self._count += 1


#     def decrement(self):
#         if not self.dropped_to_zero:
#             if self._count == 0:
#                 raise ValueError("Alive count already dropped to 0")
#             self._count -= 1
#             if self._count == 0:
#                 self._dropped_to_zero = True
#                 for callback in self._on_zero_alive_callbacks: callback()


#     def zero(self):
#         self._count = 0
#         self._dropped_to_zero = True
#         for callback in self._on_zero_alive_callbacks: callback()


#     def on_zero_alive(self, func: Callable[[], None]):
#         self._on_zero_alive_callbacks.append(func)


# T = TypeVar("T")

# class FutureOutput(Generic[T]):
#     __slots__ = '_id', '_data', '_invokation_ref'
#     def __init__(self, output: T, invokation: "Invokation"):
#         self._id = uuid.uuid4().hex
#         self._data: T = output
#         self._invokation_ref: ReferenceType["Invokation"] = ref(invokation)

#     @property
#     def id(self) -> str:
#         return self._id
    
#     @property
#     def data(self) -> T:
#         return self._data
    
    
#     @property
#     def invokation(self) -> "Invokation":
#         return self._invokation_ref()
    

#     @property
#     def chain(self) -> list["Invokation"]:
#         return self._invokation_ref().chain
    
    

#     def add_next(self, invokation: "Invokation"):
#         self.invokation.add_next(invokation)


#     def processed(self):
#         self.invokation.one_output_processed()



# D = TypeVar("D")
# class Invokation(Generic[D]):
#     __slots__ = (
#         'id', 
#         '_route', 
#         'outputs', 
#         'inside', 
#         'prev', 
#         'nexts',
#         '_event',
#         '_marked_completed', 
#         '_on_output_callbacks', 
#         '_on_next_callbacks', 
#         '_on_complete_callbacks', 
#         '_on_chain_dead_callbacks', 
#         '_unprocessed_output_count_ref', 
#         '_alive_chain_count_ref', 
#         '_future',
#         '__weakref__'
#     )

#     def __init__(self, id=None):
#         self.id = id or uuid.uuid4().hex
#         self._route = None
#         self.outputs: list[FutureOutput[D]] | None = None
#         self.inside: Invokation | None = None
#         self.prev: ReferenceType["Invokation"] | None = None
#         self.nexts: list["Invokation"] | None = None
#         self._event = asyncio.Condition()
#         self._marked_completed = False
#         self._on_output_callbacks: list[Callable[[FutureOutput], None]] = []
#         self._on_next_callbacks: list[Callable[["Invokation"], None]] = []
#         self._on_complete_callbacks: list[Callable[[list[FutureOutput]], None]] = []
#         self._on_chain_dead_callbacks: list[Callable[["FutureOutput"], None]] = []
#         self._unprocessed_output_count_ref: AliveCountRef = AliveCountRef()
#         self._alive_chain_count_ref: AliveCountRef = AliveCountRef(1)

#         def if_chain_dead():
#             if not self.nexts: 
#                 for callback in self._on_chain_dead_callbacks: callback()
#         self._unprocessed_output_count_ref.on_zero_alive(lambda: if_chain_dead())
#         self._unprocessed_output_count_ref.on_zero_alive(lambda: self._alive_chain_count_ref.decrement())

#         self._future: asyncio.Future[list[FutureOutput[D]]] = asyncio.Future()


#     @classmethod
#     def wraps(cls, inside: "Invokation", *args, **kwargs):
#         self = cls(*args, **kwargs)
#         self.inside = inside
#         self.inside.on_chain_dead(lambda output: self.add_output(output.data))
#         self.inside.on_all_chains_dead(lambda: self.mark_completed())
#         return self


#     @property
#     def route(self) -> str:
#         return self._route


#     @property
#     def chain(self) -> list["Invokation"]:
#         if self.prev:
#             prev = self.prev()
#             if prev is None: 
#                 raise ValueError("Potential bug! Previous got referenced. Unable to form chain")
#             return [*prev.chain, self]
#         return [self]

    
#     @property
#     def unprocessed_outputs_count(self) -> int:
#         return self._unprocessed_output_count_ref.count

#     @property
#     def is_completed(self) -> bool:
#         return self._marked_completed
       

#     @property
#     def is_dead(self) -> bool:
#         return self._unprocessed_output_count_ref.dropped_to_zero
    

#     @property
#     def chain_count(self) -> int:
#         if self.nexts:
#             total = 0
#             for next in self.nexts:
#                 total += next.chain_count
#             return total
#         return 1

    
#     @property
#     def is_end_of_chain(self) -> bool:
#         return self.is_dead and not self.nexts
    

#     @property
#     def is_chain_dead(self) -> bool:
#         return self._alive_chain_count_ref.dropped_to_zero

    
#     def __matmul__(self, other: str) -> "Invokation":
#         if self._route:
#             self._route = other.strip('/') + '/' + self._route
#         else:
#             self._route = other.strip('/') + '/'
#         if self.inside: self.inside @ other
#         return self
        

#     def __await__(self):
#         return self._future.__await__()
    

#     def __aiter__(self):
#         return self._iter_outputs()
    
    
#     async def _iter_outputs(self):
#         idx = 0
#         while True:
#             # fast-path
#             if self.outputs and idx < len(self.outputs):
#                 item = self.outputs[idx]
#                 idx += 1
#                 yield item
#                 continue

#             if self.is_completed:
#                 if not self.outputs:
#                     raise ValueError("Invokation marked complete without any output. Likely, calling the agent is not invoking it.")
#                 return

#             async with self._event:
#                 # double-check the condition under the lock to avoid missed wakeups
#                 should_wait = (not self.is_completed) and (not self.outputs or idx >= len(self.outputs))
#                 if should_wait:
#                     await self._event.wait()


#     def add_output(self, output: D):
#         if self.is_completed:
#             raise ValueError("Cannot add new output after marking this invokation complete")
#         o = FutureOutput(output, self)
#         if self.outputs:
#             self.outputs.append(o)
#         else:
#             self.outputs = [o]
#         self._unprocessed_output_count_ref.increment()
#         async def _notify():
#             async with self._event:
#                 self._event.notify_all()
#         asyncio.create_task(_notify())
#         for callback in self._on_output_callbacks: callback(o)


    
#     def add_next(self, next: "Invokation"):
#         if self.is_dead:
#             raise ValueError("Cannot chain new invokation after marking this output dead")
#         next._register_on_chain_dead_callbacks(self._on_chain_dead_callbacks)
#         if self.nexts: self.nexts.append(next)
#         else: self.nexts = [next]
#         self._alive_chain_count_ref.increment()
#         next.on_all_chains_dead(lambda _: self._alive_chain_count_ref.decrement())
#         next.prev = ref(self)
#         for callback in self._on_next_callbacks: callback(next)

    
#     def one_output_processed(self):
#         self._unprocessed_output_count_ref.decrement()


#     def mark_completed(self):
#         if self.is_completed:
#             raise ValueError("Invokation already marked completed once")
#         self._future.set_result(self.outputs)
#         self._marked_completed = True
#         async def _notify():
#             async with self._event:
#                 self._event.notify_all()
#         asyncio.create_task(_notify())
#         for callback in self._on_complete_callbacks: callback(self.outputs)
#         if not self.outputs: self._unprocessed_output_count_ref.zero()


#     def on_output(self, func: Callable[[FutureOutput[D]], None]):
#         self._on_output_callbacks.append(func)


#     def on_complete(self, func: Callable[[list[FutureOutput[D]]], None]):
#         self._on_complete_callbacks.append(func)


#     def on_next(self, func: Callable[["Invokation"], None]):
#         self._on_next_callbacks.append(func)


#     def on_dead(self, func: Callable[[], None]):
#         self._unprocessed_output_count_ref.on_zero_alive(func)


#     def on_chain_dead(self, func: Callable[["FutureOutput"], None]):
#         self._on_chain_dead_callbacks.append(func)
#         if self.nexts: 
#             for next in self.nexts: next.on_chain_dead(func)


#     def _register_on_chain_dead_callbacks(self, funcs: list[Callable[[FutureOutput], None]]):
#         self._on_chain_dead_callbacks.extend(funcs)
#         if self.nexts: 
#             for next in self.nexts: next._register_on_chain_dead_callbacks(funcs)


#     def on_all_chains_dead(self, func: Callable[[FutureOutput], None]):
#         self._alive_chain_count_ref.on_zero_alive(func)    
    

#     def find_by_id(self, id: str) -> Invokation | None:
#         if self.id == id:
#             return self
#         for next in self.nexts:
#             found = next.find_by_id(id)
#             if found:
#                 return found
#         if self.inside:
#             return self.inside.find_by_id(id)
        
#         raise ValueError(f"InvokationChain with id {id} not found in chain starting with {self.id}")

    
#     def normalise(self) -> list[list["Invokation"]]:
#         chains = []
#         if self.nexts:
#             for next in self.nexts:
#                 chains.extend(next.normalise())
#             return chains
#         else:
#             return [self.chain]
