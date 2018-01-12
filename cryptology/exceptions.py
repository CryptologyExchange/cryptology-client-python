from datetime import datetime

import aiohttp


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
    pass


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
