import functools
import json
import os
from collections import namedtuple
from datetime import datetime
from typing import Tuple, ClassVar, Any

import xdrlib
import aiohttp
import asyncio
import pytest
import pytz as pytz

from cryptology import ClientWriterStub, Keys, run_client, exceptions, crypto, RateLimit, CryptologyError, \
    InvalidSequence
from cryptology.common import ServerMessageType


SERVER_PORT = 8082
SERVER_URL = 'ws://127.0.0.1:{}'.format(SERVER_PORT)
Order = namedtuple('Order', ('order_id', 'amount', 'price', 'client_order_id'))


SERVER_TEST_KEYS = Keys.load('./tests/server_test.pub', './tests/server_test.priv')
CLIENT_TEST_KEYS = Keys.load('./tests/client_test.pub', './tests/client_test.priv')


class TrackingList(list):
    def track(self, item: 'AuthProtocol') -> 'TrackingListContext':
        return TrackingListContext(self, item)


class TrackingListContext:
    __slots__ = ('_parent', '_item')

    _parent: TrackingList
    _item: 'AuthProtocol'

    def __init__(self, parent: TrackingList, item: 'AuthProtocol') -> None:
        self._parent = parent
        self._item = item

    def __enter__(self) -> None:
        assert self._item not in self._parent
        self._parent.append(self._item)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        assert self._item in self._parent
        self._parent.remove(self._item)


class AuthProtocol(aiohttp.web.WebSocketResponse):
    server_keys: crypto.Keys
    symmetric_key: bytes
    server_cipher: crypto.Cipher
    client_id: str
    ACTIVE_HANDLERS: ClassVar[TrackingList] = TrackingList()
    error_code: ClassVar[int] = None

    def __init__(self, server_keys: crypto.Keys) -> None:

        super().__init__()
        self.server_keys = server_keys
        self.symmetric_key = os.urandom(32)
        self.server_cipher = crypto.Cipher(self.symmetric_key)
        self.client_version = 1

    async def send_message(self, xdr: xdrlib.Packer) -> None:
        await self.send_bytes(self.server_cipher.encrypt(xdr.get_buffer()))

    async def run(self, request: aiohttp.web.BaseRequest) -> 'AuthProtocol':
        await self.prepare(request)

        with self.ACTIVE_HANDLERS.track(self):
            self.client_id, sequence_id, last_seen_order, client_keys, client_cipher = \
                await self._crypto_handshake()
            await self.process_error_code()
        return self

    async def _crypto_handshake(self) -> Tuple[str, int, int, crypto.Keys, crypto.Cipher]:
        data = await self.receive_bytes(timeout=3)
        unpacker = xdrlib.Unpacker(self.server_keys.decrypt(data))
        client_id = unpacker.unpack_bytes().decode('ascii')

        last_seen_order = unpacker.unpack_hyper()
        client_aes_key = unpacker.unpack_bytes()
        try:
            self.client_version = unpacker.unpack_uint()
        except EOFError:
            pass

        client_keys = CLIENT_TEST_KEYS
        if client_keys is None:
            raise exceptions.ClientNotFound()

        sequence_id = 1

        data_to_sign = os.urandom(32)
        packer = xdrlib.Packer()
        packer.pack_bytes(data_to_sign)
        packer.pack_hyper(sequence_id)
        packer.pack_bytes(self.symmetric_key)
        await self.send_bytes(client_keys.encrypt(packer.get_buffer()))

        signature = await self.receive_bytes(timeout=3)
        client_keys.verify(signature, data_to_sign)

        return client_id, sequence_id, last_seen_order, client_keys, crypto.Cipher(client_aes_key)

    async def process_error_code(self):
        while True:
            await asyncio.sleep(.1)
            if self.error_code:
                error_code = self.error_code
                AuthProtocol.error_code = None
                await self.close(code=error_code)
                break

    @classmethod
    async def shutdown(cls):
        assert cls.ACTIVE_HANDLERS
        await asyncio.wait(
            [ws.close(code=1012) for ws in cls.ACTIVE_HANDLERS],
            return_when=asyncio.ALL_COMPLETED
        )

    @classmethod
    def prepare_error_code(cls, error_code):
        cls.error_code = error_code

    def __eq__(self, other):
        return id(self) == id(other)

    @classmethod
    async def send_test_order(cls, order_id: int, ts: datetime, payload: dict):
        assert cls.ACTIVE_HANDLERS
        await asyncio.wait(
            [ws._send_test_order(order_id, ts, payload) for ws in cls.ACTIVE_HANDLERS],
            return_when=asyncio.ALL_COMPLETED
        )

    async def _send_test_order(self, order_id: int, ts: datetime, payload: dict):
        packer = xdrlib.Packer()
        packer.pack_enum(ServerMessageType.OUTBOX_MESSAGE.value)
        packer.pack_hyper(order_id)
        packer.pack_double(ts.timestamp())
        packer.pack_string(json.dumps(payload).encode('utf-8'))
        await self.send_message(packer)


async def create_test_server(loop: asyncio.AbstractEventLoop) -> asyncio.AbstractServer:
    server = aiohttp.web.Server(
        lambda request: AuthProtocol(SERVER_TEST_KEYS).run(request),
        loop=loop
    )
    return await loop.create_server(server, '0.0.0.0', SERVER_PORT)


async def test_connect() -> None:
    async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
        await asyncio.sleep(.1)

    async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
        await asyncio.sleep(.1)

    loop = asyncio.get_event_loop()

    try:
        server = await create_test_server(loop)
        loop.call_later(1, server.close)

        client_coro = run_client(
            client_id='test',
            client_keys=CLIENT_TEST_KEYS,
            ws_addr=SERVER_URL,
            server_keys=SERVER_TEST_KEYS,
            writer=writer,
            read_callback=read_callback,
            last_seen_order=0
        )

        task = loop.create_task(client_coro)
        loop.call_later(2, task.cancel)

        try:
            with pytest.raises(exceptions.Disconnected):
                await task
        except asyncio.CancelledError:
            pass
    finally:
        await server.wait_closed()


async def test_restart() -> None:
    async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
        await asyncio.sleep(4)

    async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
        await asyncio.sleep(4)

    loop = asyncio.get_event_loop()

    server = await create_test_server(loop)
    loop.call_later(6, server.close)

    def make_server_restart_task() -> None:
        loop.create_task(AuthProtocol.shutdown())

    loop.call_later(1, make_server_restart_task)

    client_coro = run_client(
        client_id='test',
        client_keys=CLIENT_TEST_KEYS,
        ws_addr=SERVER_URL,
        server_keys=SERVER_TEST_KEYS,
        writer=writer,
        read_callback=read_callback,
        last_seen_order=0
    )

    task = loop.create_task(client_coro)
    loop.call_later(2, task.cancel)

    try:
        with pytest.raises(exceptions.ServerRestart):
            await task
    except asyncio.CancelledError:
        pass

    await server.wait_closed()


async def base_test_error_code(code: int, exc: CryptologyError) -> None:
    async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
        await asyncio.sleep(4)

    async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
        await asyncio.sleep(4)

    loop = asyncio.get_event_loop()

    server = await create_test_server(loop)
    loop.call_later(6, server.close)

    loop.call_later(1, functools.partial(AuthProtocol.prepare_error_code, code))

    client_coro = run_client(
        client_id='test',
        client_keys=CLIENT_TEST_KEYS,
        ws_addr=SERVER_URL,
        server_keys=SERVER_TEST_KEYS,
        writer=writer,
        read_callback=read_callback,
        last_seen_order=0
    )

    task = loop.create_task(client_coro)
    loop.call_later(2, task.cancel)

    try:
        with pytest.raises(exc):
            await task
    except asyncio.CancelledError:
        pass

    await server.wait_closed()


async def test_rate_limit() -> None:
    await base_test_error_code(code=4009, exc=RateLimit)


async def test_invalid_sequence() -> None:
    await base_test_error_code(code=4001, exc=InvalidSequence)


async def test_order_receiving() -> None:
    test_order_id = 1000
    test_ts = datetime.now().replace(microsecond=0)
    test_payload = {'test': 1}

    assertion_error = None
    test_finished = False

    async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
        await asyncio.sleep(10)

    async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
        try:
            assert order == test_order_id
            assert pytz.UTC.localize(ts) == test_ts.astimezone(pytz.UTC)
            assert payload == test_payload
        except AssertionError as e:
            nonlocal assertion_error
            assertion_error = e
        else:
            nonlocal test_finished
            test_finished = True
        await asyncio.sleep(10)

    loop = asyncio.get_event_loop()

    server = await create_test_server(loop)
    loop.call_later(6, server.close)

    send_test_order_task = None

    def send_test_order() -> None:
        nonlocal send_test_order_task
        send_test_order_task = loop.create_task(AuthProtocol.send_test_order(order_id=test_order_id,
                                                                             ts=test_ts,
                                                                             payload=test_payload))

    loop.call_later(2, send_test_order)

    client_coro = run_client(
        client_id='test',
        client_keys=CLIENT_TEST_KEYS,
        ws_addr=SERVER_URL,
        server_keys=SERVER_TEST_KEYS,
        writer=writer,
        read_callback=read_callback,
        last_seen_order=0
    )

    task = loop.create_task(client_coro)
    loop.call_later(5, task.cancel)

    try:
        await task
    except asyncio.CancelledError:
        pass
    await send_test_order_task
    await server.wait_closed()

    if assertion_error:
        raise assertion_error
    assert test_finished

