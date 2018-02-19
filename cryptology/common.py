from datetime import timedelta
from enum import Enum, unique
from typing import Any

import aiohttp

HEARTBEAT_INTERVAL = timedelta(seconds=2)

CLOSE_MESSAGES = (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING,
                  aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR,)


class ByValue(Enum):
    @classmethod
    def by_value(cls, value: int) -> Any:
        for val in cls:
            if val.value == value:
                return val
        raise IndexError(value)


@unique
class ClientMessageType(ByValue):
    INBOX_MESSAGE = 1
    RPC_REQUEST = 2


@unique
class ServerMessageType(ByValue):
    OUTBOX_MESSAGE = 1
    RPC_RESPONSE = 2
    ERROR_MESSAGE = 3
    BROADCAST_MESSAGE = 4
