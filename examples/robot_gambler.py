import asyncio
import logging
import os
import random

from aiohttp import WSServerHandshakeError, ClientConnectorError
from cryptology import ClientWriterStub, Keys, run_client, exceptions
from datetime import datetime
from decimal import Context, ROUND_DOWN, Decimal
from pathlib import Path
from typing import Optional


SERVER = os.getenv('SERVER', 'ws://127.0.0.1:8080')
NAME = Path(__file__).stem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(NAME)


async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
    while True:
        sequence_id += 1
        buy = random.choice([True, False])
        context = Context(prec=8, rounding=ROUND_DOWN)
        amount = context.create_decimal_from_float(random.random() * 0.001 + 0.00000001)
        amount = amount.quantize(Decimal(10) ** -8)
        trade_pair = random.choice(
            ('BTC_USD', 'ETH_USD', 'BCH_USD', 'LTC_USD', 'BTC_EUR', 'ETH_EUR', 'BCH_EUR', 'LTC_EUR', 'ETH_BTC',)
        )

        if buy:
            logger.info(f'buying {amount} of {trade_pair}')
        else:
            logger.info(f'selling {amount} of {trade_pair}')

        msg = {
            '@type': 'PlaceBuyFoKOrder' if buy else 'PlaceSellFoKOrder',
            'trade_pair': trade_pair,
            'amount': str(amount),
            'price': '1000000000' if buy else '0.00000001',
        }
        await ws.send_signed_message(sequence_id=sequence_id, payload=msg)
        await asyncio.sleep(0.19)


async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
    logger.debug(f'received: {order}, {ts}, {payload}')


async def throttling(level: int, sequence_id: int, order_id: int) -> bool:
    logger.warning(f'OMG!!! {level} queued messages. Slow down!')
    return False


async def main(loop: Optional[asyncio.AbstractEventLoop] = None):
    random.seed()
    client_keys = Keys.load(NAME + '.pub', NAME + '.priv')
    server_keys = Keys.load('cryptology.pub', None)

    logger.info(f'connecting to {SERVER}')

    while True:
        try:
            await run_client(
                client_id=NAME,
                client_keys=client_keys,
                ws_addr=SERVER,
                server_keys=server_keys,
                writer=writer,
                read_callback=read_callback,
                throttling_callback=throttling,
                last_seen_order=-1,
                loop=loop
            )
        except exceptions.RateLimit:
            logger.error('rate limit reached')
        except exceptions.ServerRestart:
            logger.warning('server restart')
            await asyncio.sleep(80)
        except exceptions.InvalidKey:
            logger.critical('the public key does not match client name')
            break
        except (exceptions.CryptologyConnectionError, ClientConnectorError, WSServerHandshakeError) as ex:
            logger.error(ex)
            await asyncio.sleep(30)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop=loop))
