=====
Usage
=====

.. code-block:: python3

    import asyncio
    from datetime import datetime

    from cryptology import ClientWriterStub, Keys, run_client

    async def main() -> None:
        client_keys = Keys.load('keys/test.pub', 'keys/test.priv')
        server_keys = Keys.load('keys/cryptology.pub', None)

        async def writer(ws: ClientWriterStub, sequence_id: int) -> None:
            while True:
                await asyncio.sleep(1)
                sequence_id += 1
                await ws.send_signed(
                    sequence_id=sequence_id,
                    payload={'@type': 'PlaceBuyLimitOrder', 'trade_pair': 'BTC_USD',
                             'amount': '2.3', 'price': '15000.1',
                             'client_order_id': 123 + sequence_id}
                )

        async def read_callback(order: int, ts: datetime, payload: dict) -> None:
            print(order, ts, payload)

        await run_client(
            client_id='test',
            client_keys=client_keys,
            ws_addr='ws://127.0.0.1:8080',
            server_keys=server_keys,
            writer=writer,
            read_callback=read_callback,
            last_seen_order=-1
        )
