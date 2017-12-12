from datetime import timedelta

import aiohttp

HEARTBEAT_INTERVAL = timedelta(seconds=2)

CLOSE_MESSAGES = (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSING,
                  aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR,)
