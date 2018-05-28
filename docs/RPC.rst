============================
Remote Procedure calls (RPC)
============================


Usage example
=============

.. code-block:: python3

    async def main():
        client_keys = Keys.load('keys/test.pub', 'keys/test.priv')
        server_keys = Keys.load('keys/cryptology.pub', None)

        sequence_id = 1

        ...
        async def read_callback(ws: ClientWriterStub, order: int, ts: datetime, payload: dict) -> None:
            rpc_response = await ws.send_signed_request(payload={'@type': 'UserOrdersRequest'})
            if rpc_response['@type'] == 'UserOrdersResponse':
                pprint.pprint(rpc_response)

        await run_client(
            client_id='test',
            client_keys=client_keys,
            ws_addr='ws://127.0.0.1:8080',
            server_keys=server_keys,
            writer=writer,
            read_callback=read_callback,
            last_seen_order=-1
        )


Full active orders list
=======================

- ``UserOrdersRequest``
    request of the full active order list for the account

    .. code-block:: json

        {
            "@type": "UserOrdersRequest"
        }

- ``UserOrdersResponse``
    result of ``UserOrdersRequest`` execution

    .. code-block:: json

        {
            "@type": "UserOrdersResponse",
            "order_books": {
                "BTC_USD": {
                    "buy": [{
                        "order_id": 1,
                        "amount": 42,
                        "price": 555,
                        "client_order_id": 123
                    }],
                    "sell": []
                },
                "ETH_USD": {
                    "buy": [
                        {
                            "order_id": 2,
                            "amount": 1,
                            "price": 10,
                            "client_order_id": 124
                        },
                        {
                            "order_id": 3,
                            "amount": 2,
                            "price": 11,
                            "client_order_id": 125
                        }
                    ],
                    "sell": []
                }
            }
        }


Balance of the account
=======================

- ``UserBalanceRequest``
    request of the up to date balance

    .. code-block:: json

        {
            "@type": "UserBalanceRequest"
        }

- ``UserBalanceResponse``
    result of ``UserBalanceRequest`` execution

    .. code-block:: json

        {
            "@type": "UserBalanceResponse",
            "account_id": "user",
            "balances": {
                "BTC": {
                    "available": "3.1415",
                    "on_hold": "42"
                },
                "USD": {
                    "available": "1000000",
                    "on_hold": "0"
                }
            }
        }
