import asyncio
from typing import Awaitable, Iterable, Optional

__all__ = ('run_parallel',)


async def run_parallel(coros: Iterable[Awaitable[None]],
                       *,
                       raise_canceled: bool = False,
                       loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    """
    run coros in parallel, cancel all on first exit
    raises first non-canceled exception
    may raise `asyncio.CanceledError` when `raise_canceled` is set
    """
    tasks = list(asyncio.Task(x, loop=loop) for x in coros)

    if not tasks:
        return

    def cancel_others(target: asyncio.Task) -> None:
        for other in tasks:
            if other is not target:
                other.cancel()

    for task in tasks:
        task.add_done_callback(cancel_others)

    result = await asyncio.gather(*tasks, return_exceptions=True, loop=loop)

    exception = None
    for err in filter(None, result):
        skip_canceled = exception is not None or not raise_canceled
        is_canceled = isinstance(err, asyncio.CancelledError)
        if is_canceled and skip_canceled:
            continue
        exception = err
        if not is_canceled:
            break

    if exception is not None:
        raise exception
