import asyncio
import functools
import inspect
import json
import os
import xdrlib
from datetime import datetime
from typing import Any, AsyncIterator, Awaitable, Callable, ClassVar, Optional, Tuple, Type, cast

import aiohttp

from . import common, crypto, exceptions, parallel

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

    async def handshake(self, last_seen_order: int) -> Tuple[int, crypto.Cipher]:
        init = xdrlib.Packer()
        init.pack_int(self.version)
        init.pack_string(self.client_id.encode('utf-8'))
        init.pack_hyper(last_seen_order)
        await self._send_xdr(init)

        signature_request = await self._receive_xdr(timeout=3)
        server_version = signature_request.unpack_int()
        if server_version != self.version:
            raise exceptions.IncompatibleVersion(f'server version {server_version}')
        signature_data = signature_request.unpack_bytes()

        signature = self.client_keys.sign(signature_data)
        signature_response = xdrlib.Packer()
        signature_response.pack_bytes(signature)
        await self._send_xdr(signature_response)

        server_symmteric_key = await self._key_exchange()
        server_cipher = crypto.Cipher(server_symmteric_key)

        _, data = crypto.decrypt_and_verify(
            self.server_keys, server_cipher, await self.receive_bytes(timeout=3))
        xdr = xdrlib.Unpacker(data)
        sequence_id = xdr.unpack_hyper()
        return sequence_id, server_cipher

    async def _key_exchange(self) -> bytes:
        server_symmetric_key_encrypted = await self.receive_bytes(timeout=2)
        server_symmetric_key = self.client_keys.decrypt(server_symmetric_key_encrypted)
        await self.send_bytes(self.server_keys.encrypt(self.symmetric_key))
        return server_symmetric_key

    async def send_signed(self, *, sequence_id: int, payload: dict) -> None:
        xdr = xdrlib.Packer()
        xdr.pack_hyper(sequence_id)
        xdr.pack_bytes(json.dumps(payload).encode('utf-8'))
        await self.send_bytes(crypto.encrypt_and_sign(self.client_keys, self.client_cipher, xdr.get_buffer()))

    async def receive_iter(self, server_cipher: crypto.Cipher) -> AsyncIterator[Tuple[int, datetime, dict]]:
        last_heartbeat = datetime.utcnow()
        while True:
            next_heartbeat = last_heartbeat + common.HEARTBEAT_INTERVAL * 1.5

            receive_timeout = (next_heartbeat - datetime.utcnow()).total_seconds()

            # if handling message took too long we should already have
            # next message in read buffer
            if receive_timeout <= 0:
                receive_timeout = 0.01

            try:
                data = await self.receive_bytes(timeout=receive_timeout)

            except asyncio.TimeoutError:
                raise exceptions.HeartbeatError(last_heartbeat, datetime.utcnow())

            if data == b'\x00':
                last_heartbeat = datetime.utcnow()
            else:
                _, decrypted = crypto.decrypt_and_verify(self.server_keys, server_cipher, data)
                xdr = xdrlib.Unpacker(decrypted)
                outbox_id = xdr.unpack_hyper()
                ts = datetime.utcfromtimestamp(xdr.unpack_double())
                payload = json.loads(xdr.unpack_string().decode('utf-8'))
                yield outbox_id, ts, payload

    async def receive_bytes(self, *, timeout: Optional[float] = None) -> bytes:
        msg = await self.receive(timeout=timeout)
        if msg.type != aiohttp.WSMsgType.BINARY:
            self._handle_close_message(msg)
            raise exceptions.UnsupportedMessage(msg)
        return msg.data

    async def _receive_xdr(self, *, timeout: Optional[float] = None) -> xdrlib.Unpacker:
        return xdrlib.Unpacker(await self.receive_bytes(timeout=timeout))

    async def _send_xdr(self, packer: xdrlib.Packer) -> None:
        await self.send_bytes(packer.get_buffer())

    def _handle_close_message(self, msg: aiohttp.WSMessage) -> None:
        if msg.type in common.CLOSE_MESSAGES:
            if msg.type == aiohttp.WSMsgType.CLOSE:
                if msg.data == 4000:
                    raise exceptions.ConcurrentConnection()
                elif msg.data == 4001:
                    raise exceptions.InvalidSequence()
                elif msg.data == 4002:
                    raise exceptions.DuplicateClientOrderId()
                elif msg.data == 1012:
                    raise exceptions.ServerRestart()
            raise exceptions.Disconnected()


@functools.lru_cache(typed=True)
def bind_response_class(client_id: str, client_keys: Keys, server_keys: Keys) -> Type[BaseProtocolClient]:
    return cast(Type[BaseProtocolClient],
                type('BoundProtocolClient', (BaseProtocolClient,),
                     {'client_id': client_id, 'client_keys': client_keys, 'server_keys': server_keys}))


class CryptologyClientSession(aiohttp.ClientSession):
    def __init__(self, client_id: str, client_keys: Keys, server_keys: Keys, *,
                 loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        super(CryptologyClientSession, self).__init__(
            loop=loop,
            ws_response_class=bind_response_class(client_id, client_keys, server_keys))


async def client_writer_loop(ws: BaseProtocolClient, client_id: str, sequence_id: int,
                             *, loop: Optional[asyncio.AbstractEventLoop]) -> None:
    while True:
        await asyncio.sleep(5, loop=loop)
        sequence_id += 1
        await ws.send_signed(sequence_id=sequence_id, payload={'_cls': 'CreateAccountMessage', 'account_id': client_id})


class ClientWriterStub:
    async def send_signed(self, *, sequence_id: int, payload: dict) -> None:
        pass


ClientReadCallback = Callable[[int, datetime, dict], Awaitable[None]]
ClientWriter = Callable[[ClientWriterStub, int], Awaitable[None]]


async def run_client(*, client_id: str, client_keys: Keys, ws_addr: str, server_keys: Keys,
                     read_callback: ClientReadCallback, writer: ClientWriter,
                     last_seen_order: int,
                     loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    async with CryptologyClientSession(client_id, client_keys, server_keys, loop=loop) as session:
        async with session.ws_connect(ws_addr) as ws:
            sequence_id, server_cipher = await ws.handshake(last_seen_order)

            async def reader_loop():
                async for outbox_id, ts, msg in ws.receive_iter(server_cipher):
                    await read_callback(outbox_id, ts, msg)

            await parallel.run_parallel((
                reader_loop(),
                writer(ws, sequence_id)
            ), loop=loop)
