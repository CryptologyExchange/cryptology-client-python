import aiohttp
import asyncio
import json
import logging
import xdrlib

from cryptology import exceptions, common
from datetime import datetime
from decimal import Decimal
from typing import Optional

__all__ = ('run',)

logger = logging.getLogger(__name__)


async def receive_msg(ws, *, timeout: Optional[float] = None) -> bytes:
    msg = await ws.receive(timeout=timeout)
    logger.debug('received msg: ', str(msg))
    if msg.type != aiohttp.WSMsgType.BINARY:
        logger.info('close msg received')
        exceptions.handle_close_message(msg)
        raise exceptions.UnsupportedMessage(msg)
    return msg.data


async def reader_loop(ws, market_data_callback, order_book_callback, trades_callback):
    msg = await receive_msg(ws, timeout=3)
    xdr = xdrlib.Unpacker(msg)
    version = xdr.unpack_uint()
    logger.info(f'broadcast connection version {version} established')
    if version != 1:
        raise exceptions.IncompatibleVersion()
    last_heartbeat = datetime.utcnow()
    while True:
        next_heartbeat = last_heartbeat + common.HEARTBEAT_INTERVAL * 1.5
        receive_timeout = (next_heartbeat - datetime.utcnow()).total_seconds()

        # if handling message took too long we should already have
        # next message in read buffer
        if receive_timeout <= 0:
            receive_timeout = 0.01

        try:
            msg = await receive_msg(ws, timeout=receive_timeout)
        except asyncio.TimeoutError:
            raise exceptions.HeartbeatError(last_heartbeat, datetime.utcnow())

        if msg == b'\x00':
            last_heartbeat = datetime.utcnow()
            continue
        try:
            xdr = xdrlib.Unpacker(msg)
            message_type: common.ServerMessageType = common.ServerMessageType.by_value(xdr.unpack_enum())
            if message_type != common.ServerMessageType.BROADCAST_MESSAGE:
                raise exceptions.UnsupportedMessageType()
            payload = json.loads(xdr.unpack_string().decode())
            if market_data_callback is not None:
                await market_data_callback(payload)
            if payload['@type'] == 'OrderBookAgg':
                if order_book_callback is not None:
                    await order_book_callback(
                        payload['current_order_id'],
                        payload['trade_pair'],
                        payload['buy_levels'],
                        payload['sell_levels']
                    )
            elif payload['@type'] == 'AnonymousTrade':
                if trades_callback is not None:
                    await trades_callback(
                        datetime.utcfromtimestamp(payload['time'][0]),
                        payload['current_order_id'],
                        payload['trade_pair'],
                        Decimal(payload['amount']),
                        Decimal(payload['price'])
                    )
            else:
                raise exceptions.UnsupportedMessageType()
        except (KeyError, ValueError, exceptions.UnsupportedMessageType):
            logger.exception('')
            raise exceptions.CryptologyError('failed to decode data')


async def run(*, ws_addr: str, market_data_callback=None, order_book_callback=None, trades_callback=None,
              loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    async with aiohttp.ClientSession(loop=loop) as session:
        async with session.ws_connect(ws_addr) as ws:
            await reader_loop(ws, market_data_callback, order_book_callback, trades_callback)
