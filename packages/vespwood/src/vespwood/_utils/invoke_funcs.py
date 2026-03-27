from typing import Callable, Any
import inspect
import asyncio

async def invoke_funcs(funcs: list[Callable[..., Any]], *args, **kwargs):
    results = []
    tasks = []
    for fn in funcs:
        if inspect.iscoroutinefunction(fn):
            tasks.append(asyncio.create_task(fn))
        else:
            result = fn(*args, **kwargs)
            results.append(result)
        async for awaitable in asyncio.as_completed(tasks):
            result = await awaitable
            results.append(result)
    return results