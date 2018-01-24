===============
Server messages
===============


Order lifecycle
===============

After place order message is received by cryptology (TBD) following messages
will be sent over websocket connection. All order related messages are partner
specific (i.e. you can't receive any of these messages for regular user or
other partner orders).
The ``time`` parameter is a list of two integers. The first one is a UNIX
timestamp in the UTC time zone. The second value is a number of microseconds.


- ``BuyOrderPlaced``, ``SellOrderPlaced``
    order was received by cryptology. ``closed_inline`` indicates
    order was fully executed immediately, it's safe not to expect (and therefore ignore
    following messages for this order, end of order lifecycle)

    .. code-block:: json

        {
            "@type": "BuyOrderPlaced",
            "amount": "1",
            "closed_inline": false,
            "order_id": 1,
            "price": "1",
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD",
            "client_order_id": 123
        }

- ``BuyOrderAmountChanged``, ``SellOrderAmountChanged``
    order was partially executed, sets new amount

    .. code-block:: json

        {
            "@type": "BuyOrderAmountChanged",
            "amount": "1",
            "order_id": 1,
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD",
            "client_order_id": 123
        }

- ``BuyOrderCancelled``, ``SellOrderCancelled``
    order was canceled (manual, TTL, IOC, FOK, tbd), end of order lifecycle

    .. code-block:: json

        {
            "@type": "BuyOrderCancelled",
            "order_id": 1,
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD",
            "client_order_id": 123
        }

- ``BuyOrderClosed``, ``SellOrderClosed``
    order was fully executed, end of order lifecycle

    .. code-block:: json

        {
            "@type": "BuyOrderClosed",
            "order_id": 1,
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD",
            "client_order_id": 123
        }

Wallet
======

- ``SetBalance``
    sets new partner balance for given currency

    .. code-block:: json

        {
            "@type": "SetBalance",
            "balance": "1",
            "change": "1",
            "currency": "USD",
            "reason": "aaaaa",
            "time": [
                946684800,
                0
            ]
        }

- ``InsufficientFunds``
    indicates that the account doesn't have enough funds to place the order

    .. code-block:: json

        {
            "@type": "InsufficientFunds",
            "order_id": 1,
            "currency": "USD"
        }


General
=======

..
    - ``AnonymousTrade``
        indicates any trade that happens on cryptology with sensitive data removed

        .. code-block:: json

            {
                "@type": "AnonymousTrade",
                "amount": "1",
                "maker_buy": false,
                "price": "1",
                "time": [
                    946684800,
                    0
                ],
                "trade_pair": "BTC_USD"
            }


- ``OrderBookAgg``
    aggregated order book for given symbol, recalculated after each order book change
    (most likely will be throttled to reasonble interval in future). may have empty ``buy_levels``
    or ``sell_levels`` in case of empty order book. both levels dictionaries use price as key
    and volume as value

    .. code-block:: json

        {
            "@type": "OrderBookAgg",
            "buy_levels": {
                "1": "1"
            },
            "sell_levels": {
                "0.1": "1"
            },
            "trade_pair": "BTC_USD"
        }
