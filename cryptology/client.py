import aiohttp
import asyncio
import functools
import inspect
import json
import os
import xdrlib

from datetime import datetime
from typing import Any, AsyncIterator, Awaitable, Callable, ClassVar, Optional, Tuple, Type, cast

from . import common, crypto, exceptions, parallel
from .market_data_client import receive_msg

__all__ = ('ClientReadCallback', 'ClientWriter', 'ClientWriterStub', 'run_client', 'Keys',)

Keys = crypto.Keys

CLIENTWEBSOCKETRESPONSE_INIT_ARGS = list(
    inspect.signature(aiohttp.ClientWebSocketResponse.__init__).parameters.keys())[1:]


class BaseProtocolClient(aiohttp.ClientWebSocketResponse):
    version: ClassVar[int] = 1

    client_id: ClassVar[str]
    client_keys: ClassVar[Keys]
    server_keys: ClassVar[Keys]
    symmetric_key: bytes
    client_cipher: crypto.Cipher
    rpc_requests: dict
    rpc_completed: asyncio.Event

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kw = {}
        kw.update(dict(zip(CLIENTWEBSOCKETRESPONSE_INIT_ARGS, args)))
        kw.update(kwargs)
        kw.update(
            timeout=0.01,
            autoping=False,
            heartbeat=False,
        )
        super(BaseProtocolClient, self).__init__(**kw)
        self.symmetric_key = os.urandom(32)
        self.client_cipher = crypto.Cipher(self.symmetric_key)
        self.rpc_requests = dict()
        self.rpc_completed = asyncio.Event()

    async def handshake(self, last_seen_order: int) -> Tuple[int, crypto.Cipher]:
        packer = xdrlib.Packer()
        packer.pack_bytes(self.client_id.encode('ascii'))
        packer.pack_hyper(last_seen_order)
        packer.pack_bytes(self.symmetric_key)
        await self.send_bytes(self.server_keys.encrypt(packer.get_buffer()))

        response = await receive_msg(self, timeout=3)
        unpacker = xdrlib.Unpacker(self.client_keys.decrypt(response))
        data_to_sign = unpacker.unpack_bytes()
        last_seen_sequence = unpacker.unpack_hyper()
        server_aes_key = unpacker.unpack_bytes()

        await self.send_bytes(self.client_keys.sign(data_to_sign))

        return last_seen_sequence, crypto.Cipher(server_aes_key)

    async def send_signed(self, *args, **kwargs) -> None:
        return await self.send_signed_message(*args, **kwargs)

    async def send_signed_message(self, *, sequence_id: int, payload: dict) -> None:
        xdr = xdrlib.Packer()
        xdr.pack_enum(common.ClientMessageType.INBOX_MESSAGE.value)
        xdr.pack_hyper(sequence_id)
        xdr.pack_bytes(json.dumps(payload).encode('utf-8'))
        await self.send_bytes(crypto.encrypt_and_sign(self.client_keys, self.client_cipher, xdr.get_buffer()))

    async def send_signed_request(self, *, request_id: int, payload: dict) -> Any:
        xdr = xdrlib.Packer()
        xdr.pack_enum(common.ClientMessageType.RPC_REQUEST.value)
        xdr.pack_hyper(request_id)
        xdr.pack_bytes(json.dumps(payload).encode('utf-8'))
        await self.send_bytes(crypto.encrypt_and_sign(self.client_keys, self.client_cipher, xdr.get_buffer()))
        while True:
            await self.rpc_completed.wait()
            self.rpc_completed.clear()
            if request_id in self.rpc_requests:
                return self.rpc_requests.pop(request_id)

    async def receive_iter(self, server_cipher: crypto.Cipher) -> AsyncIterator[Tuple[int, datetime, dict]]:
        last_heartbeat = datetime.utcnow()
        while True:
            next_heartbeat = last_heartbeat + common.HEARTBEAT_INTERVAL * 2.1

            receive_timeout = (next_heartbeat - datetime.utcnow()).total_seconds()

            # if handling message took too long we should already have
            # next message in read buffer
            if receive_timeout <= 0:
                receive_timeout = 0.01

            try:
                data = await receive_msg(self, timeout=receive_timeout)
            except asyncio.TimeoutError:
                raise exceptions.HeartbeatError(last_heartbeat, datetime.utcnow())

            if data == b'\x00':
                last_heartbeat = datetime.utcnow()
            else:
                decrypted = server_cipher.decrypt(data)
                xdr = xdrlib.Unpacker(decrypted)
                message_type: common.ServerMessageType = common.ServerMessageType.by_value(xdr.unpack_enum())
                if message_type is common.ServerMessageType.OUTBOX_MESSAGE:
                    outbox_id = xdr.unpack_hyper()
                    ts = datetime.utcfromtimestamp(xdr.unpack_double())
                    payload = json.loads(xdr.unpack_string().decode('utf-8'))
                    yield outbox_id, ts, payload
                elif message_type is common.ServerMessageType.RPC_RESPONSE:
                    request_id = xdr.unpack_hyper()
                    payload = json.loads(xdr.unpack_string().decode('utf-8'))
                    self.rpc_requests[request_id] = payload
                    self.rpc_completed.set()
                elif message_type is common.ServerMessageType.ERROR_MESSAGE:
                    message = xdr.unpack_string().decode('utf-8')
                    if message == 'TimeoutError()':
                        raise exceptions.HeartbeatError(datetime.utcnow(), datetime.utcnow())
                    raise exceptions.CryptologyError(message)
                else:
                    raise exceptions.UnsupportedMessageType()

    async def _receive_xdr(self, *, timeout: Optional[float] = None) -> xdrlib.Unpacker:
        return xdrlib.Unpacker(await receive_msg(self, timeout=timeout))

    async def _send_xdr(self, packer: xdrlib.Packer) -> None:
        await self.send_bytes(packer.get_buffer())


@functools.lru_cache(typed=True)
def bind_response_class(client_id: str, client_keys: Keys, server_keys: Keys) -> Type[BaseProtocolClient]:
    return cast(Type[BaseProtocolClient],
                type('BoundProtocolClient', (BaseProtocolClient,),
                     {'client_id': client_id, 'client_keys': client_keys, 'server_keys': server_keys}))


class CryptologyClientSession(aiohttp.ClientSession):
    def __init__(self, client_id: str, client_keys: Keys, server_keys: Keys, *,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super().__init__(ws_response_class=bind_response_class(client_id, client_keys, server_keys), loop=loop)


class ClientWriterStub:
    async def send_signed(self, *, sequence_id: int, payload: dict) -> None:
        pass

    async def send_signed_message(self, *, sequence_id: int, payload: dict) -> None:
        pass

    async def send_signed_request(self, *, request_id: int, payload: dict) -> Any:
        pass


ClientReadCallback = Callable[[ClientWriterStub, int, datetime, dict], Awaitable[None]]
ClientWriter = Callable[[ClientWriterStub, int], Awaitable[None]]


async def run_client(*, client_id: str, client_keys: Keys, ws_addr: str, server_keys: Keys,
                     read_callback: ClientReadCallback, writer: ClientWriter,
                     last_seen_order: int = 0,
                     loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    async with CryptologyClientSession(client_id, client_keys, server_keys, loop=loop) as session:
        async with session.ws_connect(ws_addr) as ws:
            sequence_id, server_cipher = await ws.handshake(last_seen_order)

            async def reader_loop() -> None:
                async for outbox_id, ts, msg in ws.receive_iter(server_cipher):
                    asyncio.ensure_future(read_callback(ws, outbox_id, ts, msg))

            await parallel.run_parallel((
                reader_loop(),
                writer(ws, sequence_id)
            ), loop=loop)
