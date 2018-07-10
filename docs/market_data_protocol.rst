====================
Market data protocol
====================

Market data is broadcasted via non-encrypted web socket.
It is read only and has no integrity checks aside of Web Socket built-in mechanisms.


Messages
--------

- ``OrderBookAgg``
    aggregated order book for given symbol, recalculated after each order book change
    (most likely will be throttled to reasonable interval in future). May have empty dictionaries ``buy_levels``
    or ``sell_levels`` in case of an empty order book. Both dictionaries use the price as a key
    and volume as a value. ``current_order_id`` denotes the order that leads to the state of the order book.

    .. code-block:: json

        {
            "@type": "OrderBookAgg",
            "buy_levels": {
                "1": "1"
            },
            "sell_levels": {
                "0.1": "1"
            },
            "trade_pair": "BTC_USD",
            "current_order_id": 123456
        }

- ``AnonymousTrade``
    a trade has taken place. ``time`` has two parts - integer seconds and integer milliseconds UTC.
    ``maker_buy`` shows if the maker was the buyer part.

    .. code-block:: json

        {
            "@type": "AnonymousTrade",
            "time": [1530093825, 0],
            "trade_pair": "BTC_USD",
            "current_order_id": 123456,
            "amount": "42.42",
            "price": "555",
            "maker_buy": false,
        }
