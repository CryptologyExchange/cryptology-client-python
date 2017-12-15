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

- ``PlaceBuyIoCOrder``
    immediate or cancel ask

all order placement messages share same structure

.. code-block:: json

    {
        "_cls": "PlaceBuyLimitOrder",
        "trade_pair": "BTC_USD",
        "amount": "10.1",
        "price": "15000.3",
        "client_order_id": 123
    }


Order cancelation
=================

- ``CancelOrder``
    cancel any order

    .. code-block:: json

        {
            "_cls": "CancelOrder",
            "order_id": 42
        }
