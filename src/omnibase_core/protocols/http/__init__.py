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
"""

from omnibase_core.protocols.http.protocol_http_client import (
    ProtocolHttpClient,
    ProtocolHttpResponse,
)

__all__ = [
    "ProtocolHttpClient",
    "ProtocolHttpResponse",
]
