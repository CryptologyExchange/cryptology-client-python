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
    sets a new partner balance for a given currency.
    ``reason`` can be ``trade`` or ``on_hold`` for the changes caused by trades,
    ``transfer`` for balance update by depositing money or
    ``withdraw`` as a result of a withdrawal.

    .. code-block:: json

        {
            "@type": "SetBalance",
            "balance": "1",
            "change": "1",
            "currency": "USD",
            "reason": "trade",
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

- ``DepositTransactionAccepted``
    indicates transaction information when depositing funds to the account

    .. code-block:: json

        {
            "@type": "DepositTransactionAccepted",
            "currency": "BTC",
            "amount": "0.1",
            "transaction_info": {
                "to_address": "0x49293a856169d46dbf789c89b51b2ca6c7d1c4f50x4",
                "blockchain_tx_ids": [
                    "0x124129474b1dcbdb4e39436de49f7e5987f46dc4b8740966655718d7a1da699b"
                ]
            },
            "time": [
                946684800,
                0
            ]
        }


- ``WithdrawalTransactionAccepted``
    indicates transaction information when withdrawing funds from the account

    .. code-block:: json

        {
            "@type": "WithdrawalTransactionAccepted",
            "currency": "BTC",
            "amount": "0.1",
            "transaction_info": {
                "to_address": "0x49293a856169d46dbf789c89b51b2ca6c7d1c4f50x4",
                "blockchain_tx_ids": [
                    "0x124129474b1dcbdb4e39436de49f7e5987f46dc4b8740966655718d7a1da699b"
                ]
            },
            "time": [
                946684800,
                0
            ]
        }


General
=======

    - ``OwnTrade``
        sent when the account participated in a deal on either side.
        ``maker`` equals ``true`` if the account was a maker.
        ``maker_buy`` equals ``true`` if the maker side was buying.

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
                "order_id": 1,
                "client_order_id": 123
            }
