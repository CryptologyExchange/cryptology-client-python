import aiohttp
import asyncio
import json
import logging
import xdrlib

from cryptology import exceptions, common
from datetime import datetime
from decimal import Decimal
from typing import Optional, Callable, Awaitable, List

__all__ = ('run',)

logger = logging.getLogger(__name__)


async def receive_msg(ws: aiohttp.ClientWebSocketResponse, *, timeout: Optional[float] = None) -> bytes:
    msg = await ws.receive(timeout=timeout)
    if msg.type != aiohttp.WSMsgType.BINARY:
        logger.info('close msg received (type %s): %s', msg.type.name, msg.data)
        exceptions.handle_close_message(msg)
        raise exceptions.UnsupportedMessage(msg)
    return msg.data


MarketDataCallback = Callable[[dict], Awaitable[None]]
OrderBookCallback = Callable[[int, str, dict, dict], Awaitable[None]]
TradesCallback = Callable[[datetime, int, str, Decimal, Decimal], Awaitable[None]]
TradesStateChangedCallback = Callable[[List[str], bool], Awaitable[None]]


async def reader_loop(
        ws: aiohttp.ClientWebSocketResponse,
        market_data_callback: MarketDataCallback,
        order_book_callback: OrderBookCallback,
        trades_callback: TradesCallback,
        trades_state_changed_callback: TradesStateChangedCallback) -> None:
    msg = await receive_msg(ws, timeout=3)
    xdr = xdrlib.Unpacker(msg)
    version = xdr.unpack_uint()
    logger.info(f'broadcast connection version {version} established')
    while True:
        msg = await receive_msg(ws)

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
                    asyncio.ensure_future(order_book_callback(
                        payload['current_order_id'],
                        payload['trade_pair'],
                        payload.get('buy_levels', dict),
                        payload.get('sell_levels', dict)
                    ))
            elif payload['@type'] == 'AnonymousTrade':
                if trades_callback is not None:
                    asyncio.ensure_future(trades_callback(
                        datetime.utcfromtimestamp(payload['time'][0]),
                        payload['current_order_id'],
                        payload['trade_pair'],
                        Decimal(payload['amount']),
                        Decimal(payload['price'])
                    ))
            elif payload['@type'] == 'TradesDisabledOnPairs':
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
                raise exceptions.UnsupportedMessageType()
        except (KeyError, ValueError, exceptions.UnsupportedMessageType):
            logger.exception('failed to decode data')
            raise exceptions.CryptologyError('failed to decode data')


async def run(*, ws_addr: str, market_data_callback: MarketDataCallback = None,
              order_book_callback: OrderBookCallback = None,
              trades_callback: TradesCallback = None,
              trades_state_changed_callback: TradesStateChangedCallback = None,
              loop: Optional[asyncio.AbstractEventLoop] = Awaitable[None]) -> None:
    async with aiohttp.ClientSession(loop=loop) as session:
        async with session.ws_connect(ws_addr, receive_timeout=6, heartbeat=3) as ws:
            await reader_loop(ws, market_data_callback, order_book_callback, trades_callback,
                              trades_state_changed_callback)
