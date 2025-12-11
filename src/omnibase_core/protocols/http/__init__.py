"""
ONEX HTTP protocol definitions for dependency inversion.

This package provides protocol definitions for HTTP client operations,
enabling dependency inversion for HTTP libraries like aiohttp, httpx,
and requests.

Available Protocols:
- ProtocolHttpClient: Async HTTP client interface
- ProtocolHttpResponse: HTTP response interface

Usage:
    from omnibase_core.protocols.http import (
        ProtocolHttpClient,
        ProtocolHttpResponse,
    )

    async def check_service_health(
        client: ProtocolHttpClient,
        url: str,
    ) -> bool:
        response = await client.get(url, timeout=5.0)
        return response.status == 200

DI Container Registration:
    To register an HTTP client implementation with the DI container:

    # 1. Create the adapter (e.g., using aiohttp)
    import aiohttp
    from myproject.adapters import AioHttpClientAdapter

    session = aiohttp.ClientSession()
    adapter = AioHttpClientAdapter(session)

    # 2. Register with the container using protocol name
    container.register_service("ProtocolHttpClient", adapter)

    # 3. Inject into nodes via container.get_service()
    class NodeMyServiceEffect(NodeEffect):
        def __init__(self, container: ModelONEXContainer):
            super().__init__(container)
            self.http_client = container.get_service("ProtocolHttpClient")

        async def execute_effect(self) -> ModelEffectOutput:
            response = await self.http_client.get(self.health_url)
            return ModelEffectOutput(success=response.status == 200)

    See protocol_http_client.py for complete lifecycle management patterns.
"""

from omnibase_core.protocols.http.protocol_http_client import (
    ProtocolHttpClient,
    ProtocolHttpResponse,
)

__all__ = [
    "ProtocolHttpClient",
    "ProtocolHttpResponse",
]
