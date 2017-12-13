===============
Server messages
===============


Order lifecycle
===============

after place order message is received by cryptology (TBD) following messages
will be sent over websocket connection. all order related messages are partner
specific (i.e. you can't receive any of these messages for regular user or
other partner orders)

- ``BuyOrderPlacedMessage``
    order was received by cryptology. ``closed_inline`` indicates
    order was fully executed immediately, it's safe not to expect (and therefore ignore
    following messages for this order, end of order lifecycle)

    .. code-block:: json

        {
            "_cls": "BuyOrderPlacedMessage",
            "amount": "1",
            "closed_inline": false,
            "order_id": 1,
            "price": "1",
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD"
        }

- ``BuyOrderAmountChanged``
    order was partially executed, sets new amount

    .. code-block:: json

        {
            "_cls": "BuyOrderAmountChanged",
            "amount": "1",
            "order_id": 1,
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD"
        }

- ``BuyOrderCancelledMessage``
    order was canceled (manual, TTL, IOC, FOK, tbd), end of order lifecycle

    .. code-block:: json

        {
            "_cls": "BuyOrderCancelledMessage",
            "order_id": 1,
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD"
        }

- ``BuyOrderClosedMessage``
    order was fully executed, end of order lifecycle

    .. code-block:: json

        {
            "_cls": "BuyOrderClosedMessage",
            "order_id": 1,
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD"
        }

sell orders have exactly the same data structure, only names are different

- ``SellOrderPlacedMessage``
- ``SellOrderAmountChanged``
- ``SellOrderCancelledMessage``
- ``SellOrderClosedMessage``


Wallet
======

- ``SetBalanceMessage``
    sets new partner balance for given currency

    .. code-block:: json

        {
            "_cls": "SetBalanceMessage",
            "balance": "1",
            "change": "1",
            "currency": "USD",
            "reason": "aaaaa",
            "time": [
                946684800,
                0
            ]
        }


General
=======

- ``AnonymousTradeMessage``
    indicates any trade that happens on cryptology with sensitive data removed

    .. code-block:: json

        {
            "_cls": "AnonymousTradeMessage",
            "amount": "1",
            "maker_buy": false,
            "price": "1",
            "time": [
                946684800,
                0
            ],
            "trade_pair": "BTC_USD"
        }


- ``OrderBookAggMessage``
    aggregated order book for given symbol, recalculated after each order book change
    (most likely will be throttled to reasonble interval in future). may have empty ``buy_levels``
    or ``sell_levels`` in case of empty order book. both levels dictionaries use price as key
    and volume as value

    .. code-block:: json

        {
            "_cls": "OrderBookAggMessage",
            "buy_levels": {
                "1": "1"
            },
            "sell_levels": {
                "0.1": "1"
            },
            "trade_pair": "BTC_USD"
        }
