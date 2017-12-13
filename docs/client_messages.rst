===============
Client messages
===============


Order placement
===============


- ``PlaceBuyLimitOrder``
- ``PlaceBuyFoKOrder``
- ``PlaceBuyIoCOrder``

- ``PlaceSellLimitOrder``
- ``PlaceSellFoKOrder``
- ``PlaceBuyIoCOrder``

all order placement messages share same structure

.. code-block:: json

    {
        "_cls": "PlaceBuyLimitOrder",
        "trade_pair": "BTC_USD",
        "amount": "10.1",
        "price": "15000.3",
        "client_order_id": 123
    }
