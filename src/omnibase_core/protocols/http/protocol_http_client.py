"""
ONEX HTTP client protocol for dependency inversion.

This module provides the ProtocolHttpClient and ProtocolHttpResponse protocol
definitions, enabling dependency inversion for HTTP client implementations.
Components can depend on these protocols instead of concrete HTTP libraries
(aiohttp, httpx, requests), allowing for easier testing and implementation swapping.

Design Principles:
- Use typing.Protocol with @runtime_checkable for duck typing support
- Keep interfaces minimal - only define what ONEX Core actually needs
- Provide complete type hints for mypy strict mode compliance
- Support async HTTP operations with timeout and header configuration

Usage:
    from omnibase_core.protocols.http import ProtocolHttpClient, ProtocolHttpResponse

    # Use in type hints for dependency injection
    async def check_health(client: ProtocolHttpClient, url: str) -> bool:
        response = await client.get(url, timeout=5.0)
        return response.status == 200

Migration from direct imports:
    # Before (direct aiohttp import):
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            status = response.status

    # After (protocol-based):
    async def do_request(client: ProtocolHttpClient, url: str) -> int:
        response = await client.get(url)
        return response.status
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProtocolHttpResponse(Protocol):
    """
    Protocol for HTTP response objects.

    Defines the minimal interface for HTTP responses needed by ONEX Core.
    Implementations can wrap aiohttp.ClientResponse, httpx.Response,
    or requests.Response objects.

    Attributes:
        status: HTTP status code (e.g., 200, 404, 500)

    Methods:
        text(): Async method to get response body as text
        json(): Async method to parse response body as JSON
    """

    @property
    def status(self) -> int:
        """
        HTTP status code of the response.

        Returns:
            Integer status code (e.g., 200, 404, 500)
        """
        ...

    async def text(self) -> str:
        """
        Get the response body as text.

        Returns:
            Response body decoded as a string

        Raises:
            May raise implementation-specific errors for encoding issues
        """
        ...

    async def json(self) -> Any:
        """
        Parse the response body as JSON.

        Returns:
            Parsed JSON data (typically dict or list)

        Raises:
            May raise implementation-specific errors for invalid JSON
        """
        ...


@runtime_checkable
class ProtocolHttpClient(Protocol):
    """
    Protocol for HTTP client implementations.

    Defines the minimal interface for HTTP clients needed by ONEX Core.
    Implementations can wrap aiohttp.ClientSession, httpx.AsyncClient,
    or other async HTTP libraries.

    This protocol enables dependency inversion - components depend on
    this protocol rather than concrete HTTP libraries, allowing:
    - Easier unit testing with mock implementations
    - Swapping HTTP libraries without code changes
    - Consistent interface across different HTTP backends

    Example implementation wrapper for aiohttp:
        class AioHttpClientAdapter:
            def __init__(self, session: aiohttp.ClientSession):
                self._session = session

            async def get(
                self,
                url: str,
                timeout: float | None = None,
                headers: dict[str, str] | None = None,
            ) -> ProtocolHttpResponse:
                client_timeout = aiohttp.ClientTimeout(total=timeout)
                async with self._session.get(
                    url, timeout=client_timeout, headers=headers
                ) as response:
                    return AioHttpResponseAdapter(response)
    """

    async def get(
        self,
        url: str,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> ProtocolHttpResponse:
        """
        Perform an HTTP GET request.

        Args:
            url: The URL to request
            timeout: Optional timeout in seconds for the request.
                     If None, implementation-specific default is used.
            headers: Optional HTTP headers to include in the request

        Returns:
            ProtocolHttpResponse with the response data

        Raises:
            May raise implementation-specific errors for network failures,
            timeouts, or connection errors
        """
        ...


__all__ = ["ProtocolHttpClient", "ProtocolHttpResponse"]
