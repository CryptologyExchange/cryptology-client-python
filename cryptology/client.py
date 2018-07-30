import aiohttp
import asyncio
import functools
import inspect
import json
import logging
import os
import warnings
import xdrlib

from datetime import datetime
from typing import Any, AsyncIterator, Awaitable, Callable, ClassVar, Optional, Tuple, Type, cast, List

from . import common, crypto, exceptions, parallel
from .market_data_client import receive_msg

__all__ = ('ClientReadCallback', 'ClientWriter', 'ClientWriterStub', 'run_client', 'Keys',)

logger = logging.getLogger(__name__)

Keys = crypto.Keys

CLIENTWEBSOCKETRESPONSE_INIT_ARGS = list(
    inspect.signature(aiohttp.ClientWebSocketResponse.__init__).parameters.keys())[1:]


class ClientWriterStub:
    async def send_signed(self, *, sequence_id: int, payload: dict) -> None:
        pass

    async def send_signed_message(self, *, sequence_id: int, payload: dict) -> None:
        pass

    async def send_signed_request(self, *, request_id: int, payload: dict) -> Any:
        pass


ClientReadCallback = Callable[[ClientWriterStub, int, datetime, dict], Awaitable[None]]
ClientWriter = Callable[[ClientWriterStub, int], Awaitable[None]]
ClientThrottlingCallback = Callable[[int, int, int], Awaitable[bool]]
TradesStateChangedCallback = Callable[[List[str], bool], Awaitable[None]]


class BaseProtocolClient(aiohttp.ClientWebSocketResponse):
    VERSION: ClassVar[int] = 4

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
        super(BaseProtocolClient, self).__init__(**kw)
        self.symmetric_key = os.urandom(32)
        self.client_cipher = crypto.Cipher(self.symmetric_key)
        self.rpc_requests = dict()
        self.rpc_completed = asyncio.Event()
        self.send_fut = None
        self.throttle = 0

    async def handshake(self, last_seen_order: int) -> Tuple[int, crypto.Cipher, int]:
        packer = xdrlib.Packer()
        packer.pack_bytes(self.client_id.encode('ascii'))
        packer.pack_hyper(last_seen_order)
        packer.pack_bytes(self.symmetric_key)
        packer.pack_uint(self.VERSION)
        await self.send_bytes(self.server_keys.encrypt(packer.get_buffer()))
        logger.debug('sent handshake')

        response = await receive_msg(self, timeout=3)
        logger.debug('received handshake')
        unpacker = xdrlib.Unpacker(self.client_keys.decrypt(response))
        data_to_sign = unpacker.unpack_bytes()
        last_seen_sequence = unpacker.unpack_hyper()
        server_aes_key = unpacker.unpack_bytes()
        try:
            server_version = unpacker.unpack_uint()
        except EOFError:
            server_version = 1

        await self.send_bytes(self.client_keys.sign(data_to_sign))
        logger.debug('sent client key')

        return last_seen_sequence, crypto.Cipher(server_aes_key), server_version

    async def send_signed(self, *args, **kwargs) -> None:
        warnings.warn("The 'send_signed' method is deprecated, use 'send_signed_message' instead", DeprecationWarning)
        return await self.send_signed_message(*args, **kwargs)

    async def send_signed_message(self, *, sequence_id: int, payload: dict) -> None:
        if self.closed:
            logger.warning('the socket is closed')
            raise exceptions.CryptologyConnectionError()
        xdr = xdrlib.Packer()
        xdr.pack_enum(common.ClientMessageType.INBOX_MESSAGE.value)
        xdr.pack_hyper(sequence_id)
        xdr.pack_bytes(json.dumps(payload).encode('utf-8'))
        encrypted = self.client_cipher.encrypt(xdr.get_buffer())
        if self.send_fut:
            await self.send_fut
        if self.throttle:
            logger.warning('throttle for %f seconds', self.throttle)
            throttle, self.throttle = self.throttle, 0
            await asyncio.sleep(throttle)
        logger.debug('sending message with seq id %i: %s', sequence_id, payload)
        self.send_fut = asyncio.ensure_future(self.send_bytes(encrypted))

    async def send_signed_request(self, *, request_id: int, payload: dict) -> Any:
        xdr = xdrlib.Packer()
        xdr.pack_enum(common.ClientMessageType.RPC_REQUEST.value)
        xdr.pack_hyper(request_id)
        xdr.pack_bytes(json.dumps(payload).encode('utf-8'))
        logger.debug('sending RPC req with req id %i: %s', request_id, payload)
        await self.send_bytes(self.client_cipher.encrypt(xdr.get_buffer()))
        while True:
            logger.debug('waiting for RPC result')
            await self.rpc_completed.wait()
            self.rpc_completed.clear()
            if request_id in self.rpc_requests:
                logger.debug('result received')
                return self.rpc_requests.pop(request_id)

    async def receive_iter(self, server_cipher: crypto.Cipher, throttling_callback: ClientThrottlingCallback,
                           trades_state_changed_callback: TradesStateChangedCallback
                           ) -> AsyncIterator[Tuple[int, datetime, dict]]:
        while True:
            data = await receive_msg(self)

            decrypted = server_cipher.decrypt(data)
            xdr = xdrlib.Unpacker(decrypted)
            message_type: common.ServerMessageType = common.ServerMessageType.by_value(xdr.unpack_enum())
            logger.debug('message %s received', message_type)
            if message_type is common.ServerMessageType.THROTTLING_MESSAGE:
                level = xdr.unpack_int()
                sequence_id = xdr.unpack_hyper()
                order_id = xdr.unpack_hyper()
                if not throttling_callback or not await throttling_callback(level, sequence_id, order_id):
                    self.throttle = 0.001 * level
            elif message_type is common.ServerMessageType.OUTBOX_MESSAGE:
                outbox_id = xdr.unpack_hyper()
                ts = datetime.utcfromtimestamp(xdr.unpack_double())
                payload = json.loads(xdr.unpack_string().decode('utf-8'))
                logger.debug('outbox message: %s', payload)
                yield outbox_id, ts, payload
            elif message_type is common.ServerMessageType.RPC_RESPONSE:
                request_id = xdr.unpack_hyper()
                payload = json.loads(xdr.unpack_string().decode('utf-8'))
                logger.debug('RPC response: %s', payload)
                self.rpc_requests[request_id] = payload
                self.rpc_completed.set()
            elif message_type is common.ServerMessageType.ERROR_MESSAGE:
                error_type = common.ServerErrorType.by_value(xdr.unpack_int())
                message = xdr.unpack_string().decode('utf-8')
                if message == 'TimeoutError()':
                    logger.error('heartbeat error received')
                    raise exceptions.HeartbeatError(datetime.utcnow(), datetime.utcnow())
                logger.error('error received: %s', message)

                if error_type == common.ServerErrorType.UNKNOWN_ERROR:
                    raise exceptions.CryptologyError(message)
                elif error_type == common.ServerErrorType.INVALID_PAYLOAD:
                    raise exceptions.InvalidPayload(message)
                elif error_type == common.ServerErrorType.DUPLICATE_CLIENT_ORDER_ID:
                    raise exceptions.DuplicateClientOrderId()
                elif error_type == common.ServerErrorType.TRADES_DISABLED:
                    raise exceptions.TradesDisabledError()
            elif message_type == common.ServerMessageType.BROADCAST_MESSAGE:
                message = xdr.unpack_string().decode('utf-8')
                payload = json.loads(message)
                if payload['@type'] == 'TradesDisabledOnPairs':
                    if trades_state_changed_callback:
                        await trades_state_changed_callback(payload['trade_pairs'], False)
                    else:
                        logger.warning('Trades disabled for pairs {},'
                                       'but trades_state_changed_callback'
                                       ' is not seted'.format(' '.join(payload['trade_pairs'])))
                elif payload['@type'] == 'TradesEnabledOnPairs':
                    if trades_state_changed_callback:
                        await trades_state_changed_callback(payload['trade_pairs'], True)
                    else:
                        logger.warning('Trades enabled for pairs {},'
                                       'but trades_state_changed_callback'
                                       ' is not seted'.format(' '.join(payload['trade_pairs'])))
            else:
                logger.error('unsupported message type')
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


async def run_client(*, client_id: str, client_keys: Keys, ws_addr: str, server_keys: Keys,
                     read_callback: ClientReadCallback, writer: ClientWriter,
                     throttling_callback: ClientThrottlingCallback = None,
                     trades_state_changed_callback: TradesStateChangedCallback = None,
                     last_seen_order: int = 0,
                     loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    async with CryptologyClientSession(client_id, client_keys, server_keys, loop=loop) as session:
        async with session.ws_connect(ws_addr, autoclose=True, autoping=True, receive_timeout=10, heartbeat=4) as ws:
            logger.info('connected to the server %s', ws_addr)
            sequence_id, server_cipher, server_version = await ws.handshake(last_seen_order)
            logger.info('handshake succeeded, server version %i, sequence id = %i', server_version, sequence_id)

            async def reader_loop() -> None:
                async for outbox_id, ts, msg in ws.receive_iter(server_cipher, throttling_callback,
                                                                trades_state_changed_callback):
                    logger.debug('%s new msg from server @%i: %s', ts, outbox_id, msg)
                    asyncio.ensure_future(read_callback(ws, outbox_id, ts, msg))

            await parallel.run_parallel((
                reader_loop(),
                writer(ws, sequence_id)
            ), loop=loop)
