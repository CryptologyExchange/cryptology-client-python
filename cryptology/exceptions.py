import aiohttp
from cryptology.common import CLOSE_MESSAGES
from datetime import datetime


class CryptologyError(Exception):
    pass


class CryptologyProtocolError(CryptologyError):
    pass


class IncompatibleVersion(CryptologyProtocolError):
    pass


class ClientNotFound(CryptologyProtocolError):
    pass


class InvalidKey(CryptologyProtocolError):
    pass


class InvalidSequence(CryptologyProtocolError):
    pass


class DuplicateClientOrderId(CryptologyProtocolError):
    pass


class InvalidPayload(CryptologyProtocolError):
    pass


class TradesDisabledError(CryptologyError):
    pass


class UnsupportedMessage(CryptologyProtocolError):
    msg: aiohttp.WSMessage

    def __init__(self, msg: aiohttp.WSMessage) -> None:
        super(CryptologyProtocolError, self).__init__(f'unsupported message {msg!r}')
        self.msg = msg


class UnsupportedMessageType(CryptologyProtocolError):
    pass


class CryptologyConnectionError(CryptologyError):
    pass


class Disconnected(CryptologyConnectionError):
    def __init__(self, code: int) -> None:
        super().__init__(f'disconnected with code {code}')


class ConcurrentConnection(CryptologyConnectionError):
    pass


class ServerRestart(CryptologyConnectionError):
    pass


class HeartbeatError(CryptologyConnectionError):
    last_seen: datetime
    now: datetime

    def __init__(self, last_seen: datetime, now: datetime) -> None:
        super(HeartbeatError, self).__init__(f'client didn\'t receive heartbeat message in time'
                                             f', last seen {last_seen} now {now}')
        self.last_seen = last_seen
        self.now = now


class RateLimit(CryptologyConnectionError):
    pass


def handle_close_message(msg: aiohttp.WSMessage) -> None:
    if msg.type in CLOSE_MESSAGES:
        if msg.type == aiohttp.WSMsgType.CLOSE:
            if msg.data == 4000:
                raise ConcurrentConnection()
            elif msg.data == 4001:
                raise InvalidSequence()
            elif msg.data == 4009:
                raise RateLimit()
            elif msg.data == 1012:
                raise ServerRestart()
        raise Disconnected(msg.data)
