import asyncio
import logging
import os
import random

from cryptology import ClientWriterStub, Keys, run_client, exceptions
from datetime import datetime
from decimal import Context
from pathlib import Path
from typing import Optional


SERVER = os.getenv('SERVER', 'ws://127.0.0.1:8080')
NAME = Path(__file__).stem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(NAME)


async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
    if sequence_id == -1:
        logger.info('creating account')
        sequence_id += 1
        await ws.send_signed(sequence_id=sequence_id, payload={'@type': 'CreateAccount'})
        sequence_id += 1
        await ws.send_signed(sequence_id=sequence_id, payload={
            '@type': 'DepositFunds',
            'currency': 'USD',
            'amount': '1000000000'
        })
        sequence_id += 1
        await ws.send_signed(sequence_id=sequence_id, payload={
            '@type': 'DepositFunds',
            'currency': 'BTC',
            'amount': '1000000'
        })
        sequence_id += 1
        await ws.send_signed(sequence_id=sequence_id, payload={
            '@type': 'DepositFunds',
            'currency': 'ETH',
            'amount': '1000000'
        })

    while True:
        sequence_id += 1
        buy = random.choice([True, False])
        # use up to 0.1 of each currency in trades
        amount = Context(prec=4).create_decimal_from_float(random.random() * 0.1 + 0.00001)
        trade_pair = random.choice(('BTC_USD', 'ETH_USD',))

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
        await ws.send_signed(sequence_id=sequence_id, payload=msg)
        await asyncio.sleep(random.randrange(1, 30))  # sleep from 1 to 30 seconds between trades


async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
    logger.debug(f'received: {order}, {ts}, {payload}')


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
                last_seen_order=-1,
                loop=loop
            )
        except exceptions.HeartbeatError:
            logger.error('missed heartbeat')
        except exceptions.Disconnected as ex:
            logger.error(ex)
            await asyncio.sleep(20)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop=loop))
