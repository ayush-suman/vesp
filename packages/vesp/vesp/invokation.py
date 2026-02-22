from __future__ import annotations
import asyncio
from typing import Callable
import uuid
from weakref import ReferenceType, ref


class AliveCountRef:
    __slots__ = '_count', '_dropped_to_zero', '_on_zero_alive_callbacks'

    def __init__(self, start: int = 0):
        self._count: int = start
        self._dropped_to_zero: bool = False
        self._on_zero_alive_callbacks: list[Callable[[], None]] = []


    @property
    def count(self) -> int:
        return self._count


    @property
    def dropped_to_zero(self) -> bool:
        return self._dropped_to_zero


    def increment(self):
        if not self._dropped_to_zero:
            self._count += 1


    def decrement(self):
        if not self.dropped_to_zero:
            if self._count == 0:
                raise ValueError("Alive count already dropped to 0")
            self._count -= 1
            if self._count == 0:
                self._dropped_to_zero = True
                for callback in self._on_zero_alive_callbacks: callback()


    def zero(self):
        self._count = 0
        self._dropped_to_zero = True
        for callback in self._on_zero_alive_callbacks: callback()


    def on_zero_alive(self, func: Callable[[], None]):
        self._on_zero_alive_callbacks.append(func)



class Output[T]:
    __slots__ = '_id', '_data', '_invokation_ref'
    def __init__(self, output: T, invokation: "Invokation"):
        self._id = uuid.uuid4().hex
        self._data: T = output
        self._invokation_ref: ReferenceType["Invokation"] = ref(invokation)

    @property
    def id(self) -> str:
        return self._id
    
    @property
    def data(self) -> T:
        return self._data
    
    
    @property
    def invokation(self) -> "Invokation":
        return self._invokation_ref()
    

    @property
    def chain(self) -> list["Invokation"]:
        return self._invokation_ref().chain
    
    

    def add_next(self, invokation: "Invokation"):
        self.invokation.add_next(invokation)


    def processed(self):
        self.invokation.one_output_processed()


class Invokation[D]:
    __slots__ = (
        'id', 
        '_route', 
        'outputs', 
        'inside', 
        'prev', 
        'nexts',
        '_event',
        '_marked_completed', 
        '_on_output_callbacks', 
        '_on_next_callbacks', 
        '_on_complete_callbacks', 
        '_on_chain_dead_callbacks', 
        '_unprocessed_output_count_ref', 
        '_alive_chain_count_ref', 
        '_future',
        '__weakref__'
    )

    def __init__(self, id=None):
        self.id = id or uuid.uuid4().hex
        self._route = None
        self.outputs: list[Output[D]] | None = None
        self.inside: Invokation | None = None
        self.prev: ReferenceType["Invokation"] | None = None
        self.nexts: list["Invokation"] | None = None
        self._event = asyncio.Condition()
        self._marked_completed = False
        self._on_output_callbacks: list[Callable[[Output], None]] = []
        self._on_next_callbacks: list[Callable[["Invokation"], None]] = []
        self._on_complete_callbacks: list[Callable[[list[Output]], None]] = []
        self._on_chain_dead_callbacks: list[Callable[["Output"], None]] = []
        self._unprocessed_output_count_ref: AliveCountRef = AliveCountRef()
        self._alive_chain_count_ref: AliveCountRef = AliveCountRef(1)

        def if_chain_dead():
            if not self.nexts: 
                for callback in self._on_chain_dead_callbacks: callback()
        self._unprocessed_output_count_ref.on_zero_alive(lambda: if_chain_dead())
        self._unprocessed_output_count_ref.on_zero_alive(lambda: self._alive_chain_count_ref.decrement())

        self._future: asyncio.Future[list[Output[D]]] = asyncio.Future()


    @classmethod
    def wraps(cls, inside: "Invokation", *args, **kwargs):
        self = cls(*args, **kwargs)
        self.inside = inside
        self.inside.on_chain_dead(lambda output: self.add_output(output.data))
        self.inside.on_all_chains_dead(lambda: self.mark_completed())
        return self


    @property
    def route(self) -> str:
        return self._route


    @property
    def chain(self) -> list["Invokation"]:
        if self.prev:
            prev = self.prev()
            if prev is None: 
                raise ValueError("Potential bug! Previous got referenced. Unable to form chain")
            return [*prev.chain, self]
        return [self]

    
    @property
    def unprocessed_outputs_count(self) -> int:
        return self._unprocessed_output_count_ref.count

    @property
    def is_completed(self) -> bool:
        return self._marked_completed
       

    @property
    def is_dead(self) -> bool:
        return self._unprocessed_output_count_ref.dropped_to_zero
    

    @property
    def chain_count(self) -> int:
        if self.nexts:
            total = 0
            for next in self.nexts:
                total += next.chain_count
            return total
        return 1

    
    @property
    def is_end_of_chain(self) -> bool:
        return self.is_dead and not self.nexts
    

    @property
    def is_chain_dead(self) -> bool:
        return self._alive_chain_count_ref.dropped_to_zero

    
    def __matmul__(self, other: str) -> "Invokation":
        if self._route:
            self._route = other.strip('/') + '/' + self._route
        else:
            self._route = other.strip('/') + '/'
        if self.inside: self.inside @ other
        return self
        

    def __await__(self):
        return self._future.__await__()
    

    def __aiter__(self):
        return self._iter_outputs()
    
    
    async def _iter_outputs(self):
        idx = 0
        while True:
            # fast-path
            if self.outputs and idx < len(self.outputs):
                item = self.outputs[idx]
                idx += 1
                yield item
                continue

            if self.is_completed:
                if not self.outputs:
                    raise ValueError("Invokation marked complete without any output. Likely, calling the agent is not invoking it.")
                return

            async with self._event:
                # double-check the condition under the lock to avoid missed wakeups
                should_wait = (not self.is_completed) and (not self.outputs or idx >= len(self.outputs))
                if should_wait:
                    await self._event.wait()


    def add_output(self, output: D):
        if self.is_completed:
            raise ValueError("Cannot add new output after marking this invokation complete")
        o = Output(output, self)
        if self.outputs:
            self.outputs.append(o)
        else:
            self.outputs = [o]
        self._unprocessed_output_count_ref.increment()
        async def _notify():
            async with self._event:
                self._event.notify_all()
        asyncio.create_task(_notify())
        for callback in self._on_output_callbacks: callback(o)


    
    def add_next(self, next: "Invokation"):
        if self.is_dead:
            raise ValueError("Cannot chain new invokation after marking this output dead")
        next.register_on_chain_dead_callbacks(self._on_chain_dead_callbacks)
        if self.nexts: self.nexts.append(next)
        else: self.nexts = [next]
        self._alive_chain_count_ref.increment()
        next.on_all_chains_dead(lambda _: self._alive_chain_count_ref.decrement())
        next.prev = ref(self)
        for callback in self._on_next_callbacks: callback(next)

    
    def one_output_processed(self):
        self._unprocessed_output_count_ref.decrement()


    def mark_completed(self):
        if self.is_completed:
            raise ValueError("Invokation already marked completed once")
        self._future.set_result(self.outputs)
        self._marked_completed = True
        async def _notify():
            async with self._event:
                self._event.notify_all()
        asyncio.create_task(_notify())
        for callback in self._on_complete_callbacks: callback(self.outputs)
        if not self.outputs: self._unprocessed_output_count_ref.zero()


    def on_output(self, func: Callable[[Output[D]], None]):
        self._on_output_callbacks.append(func)


    def on_complete(self, func: Callable[[list[Output[D]]], None]):
        self._on_complete_callbacks.append(func)


    def on_next(self, func: Callable[["Invokation"], None]):
        self._on_next_callbacks.append(func)


    def on_dead(self, func: Callable[[], None]):
        self._unprocessed_output_count_ref.on_zero_alive(func)


    def on_chain_dead(self, func: Callable[["Output"], None]):
        self._on_chain_dead_callbacks.append(func)
        if self.nexts: 
            for next in self.nexts: next.on_chain_dead(func)


    def on_all_chains_dead(self, func: Callable[[Output], None]):
        self._alive_chain_count_ref.on_zero_alive(func)


    def register_on_next_callbacks(self, funcs: list[Callable[["Invokation"], None]]):
        self._on_next_callbacks.extend(funcs)


    def register_on_chain_dead_callbacks(self, funcs: list[Callable[[Output], None]]):
        self._on_chain_dead_callbacks.extend(funcs)
        if self.nexts: 
            for next in self.nexts: next.register_on_chain_dead_callbacks(funcs)
    

    def find_by_id(self, id: str) -> Invokation | None:
        if self.id == id:
            return self
        for next in self.nexts:
            found = next.find_by_id(id)
            if found:
                return found
        raise ValueError(f"InvokationChain with id {id} not found in chain starting with {self.id}")
    

    def copy_without_outputs(self):
        return Invokation(id=self.id)

    
    def normalise(self) -> list[list["Invokation"]]:
        chains = []
        if self.nexts:
            for next in self.nexts:
                chains.extend(next.normalise())
            return chains
        else:
            return [self.chain]