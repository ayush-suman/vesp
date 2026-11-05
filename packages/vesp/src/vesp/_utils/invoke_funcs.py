from typing import Callable, Any
import inspect
import asyncio

async def invoke_funcs(funcs: list[Callable[..., Any]], *args, **kwargs):
    results = []
    awaitables = []
    for fn in funcs:
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            awaitables.append(result)
        else:
            results.append(result)
    for awaitable in asyncio.as_completed(awaitables):
        result = await awaitable
        results.append(result)
    return results