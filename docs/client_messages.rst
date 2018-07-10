===============
Client messages
===============


Order placement
===============


- ``PlaceBuyLimitOrder``
    limit bid

- ``PlaceBuyFoKOrder``
    fill or kill bid

- ``PlaceBuyIoCOrder``
    immediate or cancel bid

- ``PlaceSellLimitOrder``
    limit ask

- ``PlaceSellFoKOrder``
    fill or kill ask

- ``PlaceSellIoCOrder``
    immediate or cancel ask

all order placement messages share the same structure

.. code-block:: json

    {
        "@type": "PlaceBuyLimitOrder",
        "trade_pair": "BTC_USD",
        "amount": "10.1",
        "price": "15000.3",
        "client_order_id": 123,
        "ttl": 0
    }

``client_order_id`` is a tag to relate server messages to client ones.
``ttl`` is the time the order is valid for. Measured in seconds (with 1 minute granularity).
0 means valid forever.


Order cancelation
=================

- ``CancelOrder``
    cancel any order

    .. code-block:: json

        {
            "@type": "CancelOrder",
            "order_id": 42
        }

- ``CancelAllOrders``
    cancel all active orders opened by the client

    .. code-block:: json

        {
            "@type": "CancelAllOrders"
        }
