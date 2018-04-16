import asyncio
import cryptology
import logging
import os
from aiohttp import WSServerHandshakeError
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional


SERVER = os.getenv('SERVER', 'ws://127.0.0.1:8080')
NAME = Path(__file__).stem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(NAME)


async def read_order_book(order_id: int, pair: str, buy: dict, sell: dict) -> None:
    if pair in ('BTC_USD', 'ETH_USD', 'BTC_EUR', 'ETH_EUR',):
        if len(buy) == 0:
            logger.error('%s buy order book has size %i @ order %i', pair, len(buy), order_id)
        if len(sell) == 0:
            logger.error('%s sell order book has size %i @ order %i', pair, len(sell), order_id)
    logger.info(f'sell orders of {pair} @{order_id}: {sell}')
    logger.info(f'buy orders of {pair} @{order_id}: {buy}')


async def read_trades(ts: datetime, order_id: int, pair: str, amount: Decimal, price: Decimal) -> None:
    currencies = pair.split("_")
    logger.info(f'{ts}@{order_id} a buy of {amount} {currencies[0]} for {price} {currencies[1]} took place')


async def main(loop: Optional[asyncio.AbstractEventLoop] = None):
    logger.info(f'connecting to {SERVER}')

    while True:
        try:
            await cryptology.run_market_data(
                ws_addr=SERVER,
                market_data_callback=None,
                order_book_callback=read_order_book,
                trades_callback=read_trades,
                loop=loop
            )
        except cryptology.exceptions.HeartbeatError:
            logger.error('missed heartbeat')
        except cryptology.exceptions.ServerRestart:
            logger.warning('server restart')
            await asyncio.sleep(80)
        except (cryptology.exceptions.Disconnected, WSServerHandshakeError) as ex:
            logger.error(ex)
            await asyncio.sleep(30)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop=loop))
