"""Connection fallback for the pinned unsigned webOS client."""

import aiohttp
from aiowebostv import WebOsClient as BaseWebOsClient
from aiowebostv.webos_client import MAIN_WS_MAX_MSG_SIZE, WS_PORT, WSS_PORT


class WebOsClient(BaseWebOsClient):
    """Try the secure port when the plain port rejects or times out."""

    async def _create_main_ws(self) -> aiohttp.ClientWebSocketResponse:
        try:
            return await self._ws_connect(
                f"ws://{self.host}:{WS_PORT}", MAIN_WS_MAX_MSG_SIZE
            )
        except (
            TimeoutError, aiohttp.ClientConnectionError, aiohttp.WSServerHandshakeError
        ):
            return await self._ws_connect(
                f"wss://{self.host}:{WSS_PORT}", MAIN_WS_MAX_MSG_SIZE
            )
