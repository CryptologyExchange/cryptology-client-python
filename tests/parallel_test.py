import asyncio
import pytest

from cryptology.parallel import run_parallel
from typing import Optional


async def target(sleep: float, exception: Optional[Exception] = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    await asyncio.sleep(sleep, loop=loop)
    if exception:
        raise exception


class FooError(Exception):
    pass


class BarError(Exception):
    pass


@pytest.mark.asyncio
async def test_exit(event_loop: asyncio.AbstractEventLoop) -> None:
    await run_parallel([target(.1, loop=event_loop), target(.2, loop=event_loop)], loop=event_loop)

    with pytest.raises(FooError):
        await run_parallel([target(.1, FooError(), loop=event_loop), target(.2, BarError(), loop=event_loop)],
                           loop=event_loop)

    with pytest.raises(asyncio.CancelledError):
        await run_parallel([target(.1, loop=event_loop), target(.2, loop=event_loop)],
                           raise_canceled=True, loop=event_loop)
