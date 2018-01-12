import asyncio
import itertools
import os
import pprint

from collections import namedtuple
from cryptology import ClientWriterStub, Keys, run_client
from datetime import datetime
from decimal import Decimal
from typing import Iterable


SERVER = os.getenv('SERVER', 'ws://127.0.0.1:8080')
Order = namedtuple('Order', ('order_id', 'amount', 'price', 'client_order_id'))


def iter_orders(payload: dict) -> Iterable[Order]:
    for book in payload['order_books'].values():
        for order in itertools.chain(book['buy'], book['sell']):
            yield Order(
                order_id=order['order_id'],
                amount=Decimal(order['amount']),
                price=Decimal(order['price']),
                client_order_id=order['client_order_id']
            )


async def main():
    client_keys = Keys.load('test.pub', 'test.priv')
    server_keys = Keys.load('cryptology.pub', None)

    sid = -2
    rid = 0

    async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
        nonlocal sid
        sid = sequence_id

        sid += 1
        await ws.send_signed_message(sequence_id=sid, payload={'@type': 'CreateAccount',})

        sid += 1
        await ws.send_signed_message(sequence_id=sid, payload={'@type': 'DepositFunds', 'currency': 'USD', 'amount': '1000000000'})

        while True:
            sid += 1
            await ws.send_signed_message(sequence_id=sid, payload={
                '@type': 'PlaceBuyLimitOrder',
                'trade_pair': 'BTC_USD',
                'price': '1',
                'amount': '1',
                'client_order_id': sid,
                'ttl': 0
            })
            await asyncio.sleep(1)

    async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
        if payload['@type'] == 'BuyOrderPlaced':
            nonlocal sid
            nonlocal rid
            rid += 1
            result = await ws.send_signed_request(request_id=rid, payload={'@type': 'UserOrdersRequest'})
            pprint.pprint(result)
            if sid == -2:
                return
            if result['@type'] == 'UserOrdersResponse':
                total_amount = sum(x.amount for x in iter_orders(result))
                if total_amount >= Decimal(3):
                    for order in iter_orders(result):
                        sid += 1
                        await ws.send_signed_message(sequence_id=sid, payload={'@type': 'CancelOrder', 'order_id': order.order_id})

    await run_client(
        client_id='test',
        client_keys=client_keys,
        ws_addr=SERVER,
        server_keys=server_keys,
        writer=writer,
        read_callback=read_callback,
        last_seen_order=-1
    )


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
