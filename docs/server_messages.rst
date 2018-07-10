===============
Server messages
===============


Order lifecycle
===============

After a place order message is received by cryptology (TBD) the following messages
will be sent over web socket connection. All order related messages are partner
specific (i.e. you can't receive any of these messages for regular user or
other partner orders).
The ``time`` parameter is a list of two integers. The first one is a UNIX
timestamp in the UTC time zone. The second value is a number of microseconds.


- ``BuyOrderPlaced``, ``SellOrderPlaced``
    order was received by cryptology. ``closed_inline`` indicates
    an order that was fully executed immediately, it’s safe not to expect (and, therefore ignore)
    other messages for this order. End of order lifecycle.
    ``initial_amount`` equals to the full order size while ``amount`` is the part
    of the order left after instant order execution and placed to the order book.

    .. code-block:: json

        {
            "@type": "BuyOrderPlaced",
            "amount": "1",
            "initial_amount": "3",
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
    order was partially executed, sets a new amount

    .. code-block:: json

        {
            "@type": "BuyOrderAmountChanged",
            "amount": "1",
            "order_id": 1,
            "fee": "0.002",
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

- ``OrderNotFound``
    attempt to cancel a non-existing order was made

    .. code-block:: json

        {
            "@type": "OrderNotFound",
            "order_id": 1
        }

Wallet
======

- ``SetBalance``
    sets a new partner balance for a given currency

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
    indicates that an account doesn't have enough funds to place an order

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

    - ``OwnTrade``
        sent when an account participated in a deal on either side.

        .. code-block:: json

            {
                "@type": "OwnTrade",
                "time": [
                    946684800,
                    0
                ],
                "trade_pair": "BTC_USD",
                "amount": "1",
                "price": "1",
                "maker": true,
                "maker_buy": false,
                "order_id": int,
            }
