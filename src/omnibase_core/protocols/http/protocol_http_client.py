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

Migration Guide:
    This section helps migrate existing code from direct HTTP library usage
    to protocol-based dependency injection.

    IMPORTANT: Adapter implementations belong in omnibase_infra, NOT omnibase_core.
    omnibase_core defines protocols (interfaces) only. Concrete implementations
    that depend on external libraries (aiohttp, httpx, etc.) must live in the
    infrastructure layer to maintain clean architecture boundaries.

    Step 1: Identify direct HTTP library imports
        # Before - tight coupling to aiohttp
        import aiohttp

        class MyService:
            async def fetch_data(self, url: str) -> dict:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        return await response.json()

    Step 2: Create an adapter implementing ProtocolHttpClient (in omnibase_infra)
        # NOTE: This adapter implementation belongs in omnibase_infra, not omnibase_core.
        # Example location: omnibase_infra/adapters/http/aiohttp_client_adapter.py
        import aiohttp
        from omnibase_core.protocols.http import (
            ProtocolHttpClient,
            ProtocolHttpResponse,
        )

        class AioHttpResponseAdapter:
            def __init__(self, status: int, body: str):
                self._status = status
                self._body = body

            @property
            def status(self) -> int:
                return self._status

            async def text(self) -> str:
                return self._body

            async def json(self) -> Any:
                import json
                return json.loads(self._body)

        class AioHttpClientAdapter:
            def __init__(self, session: aiohttp.ClientSession):
                self._session = session

            async def get(
                self,
                url: str,
                timeout: float | None = None,
                headers: dict[str, str] | None = None,
            ) -> ProtocolHttpResponse:
                client_timeout = (
                    aiohttp.ClientTimeout(total=timeout) if timeout else None
                )
                async with self._session.get(
                    url, timeout=client_timeout, headers=headers
                ) as resp:
                    body = await resp.text()
                    return AioHttpResponseAdapter(resp.status, body)

    Step 3: Refactor consuming code to use the protocol
        # After - loose coupling via protocol
        from omnibase_core.protocols.http import ProtocolHttpClient

        class MyService:
            def __init__(self, http_client: ProtocolHttpClient):
                self._client = http_client

            async def fetch_data(self, url: str) -> dict:
                response = await self._client.get(url)
                return await response.json()

    Step 4: Wire up via DI container
        # In your application setup
        # Import adapter from omnibase_infra (NOT from omnibase_core):
        from omnibase_infra.adapters.http import AioHttpClientAdapter

        session = aiohttp.ClientSession()
        adapter = AioHttpClientAdapter(session)
        container.register_service("ProtocolHttpClient", adapter)

        # Inject into services
        service = MyService(container.get_service("ProtocolHttpClient"))

Lifecycle Management:
    HTTP client implementations typically manage connection pools, sockets,
    and other resources that require proper cleanup.

    Key Principles:
    - Implementations MAY use connection pooling for performance
    - Callers MUST NOT assume ownership of the client
    - The creating code (often the DI container) is responsible for cleanup
    - Clients MAY be long-lived and shared across multiple callers

    Container-Managed Lifecycle (Recommended):
        # During application startup
        session = aiohttp.ClientSession()
        adapter = AioHttpClientAdapter(session)
        container.register_service("ProtocolHttpClient", adapter)

        # During application shutdown (via shutdown hook)
        await session.close()

    Local Lifecycle (When Needed):
        # If you must create a client locally, use context managers
        async with aiohttp.ClientSession() as session:
            adapter = AioHttpClientAdapter(session)
            result = await adapter.get(url)
        # Session automatically closed

    Testing Lifecycle:
        # In tests, create fresh mock per test to avoid state leakage
        @pytest.fixture
        def mock_http_client() -> ProtocolHttpClient:
            client = Mock(spec=ProtocolHttpClient)
            client.get = AsyncMock(return_value=mock_response)
            return client

Error Handling:
    Implementations should translate library-specific exceptions to standard
    Python exceptions where possible.

    Expected Exception Types:
    - TimeoutError: Request exceeded the specified timeout
    - ConnectionError: Network connectivity issues (DNS, connection refused)
    - ValueError: Invalid URL or parameters
    - Implementation-specific: Other errors may vary by implementation

    Example Error Handling:
        async def safe_health_check(
            client: ProtocolHttpClient,
            url: str,
        ) -> tuple[bool, str | None]:
            try:
                response = await client.get(url, timeout=5.0)
                return response.status == 200, None
            except TimeoutError:
                return False, "Request timed out"
            except ConnectionError:
                return False, "Connection failed"
            except Exception as e:  # Example: Catch-all for other HTTP client errors
                return False, f"Unexpected error: {e}"

    Note: Callers should handle both standard exceptions and be prepared
    for implementation-specific exceptions from the underlying HTTP library.
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

    IMPORTANT - Architecture Boundary:
        This protocol is defined in omnibase_core. Concrete implementations
        (e.g., AioHttpClientAdapter, HttpxClientAdapter) belong in omnibase_infra,
        NOT in omnibase_core. This maintains clean architecture separation:

        - omnibase_core: Protocols (interfaces) only - no external dependencies
        - omnibase_infra: Concrete implementations with external library dependencies

        Example implementation location: omnibase_infra/adapters/http/

    This protocol enables dependency inversion - components depend on
    this protocol rather than concrete HTTP libraries, allowing:
    - Easier unit testing with mock implementations
    - Swapping HTTP libraries without code changes
    - Consistent interface across different HTTP backends

    Lifecycle Management:
        Implementations MAY be long-lived (e.g., connection pooling).
        Callers MUST NOT assume ownership - cleanup is implementation-defined.
        For ONEX Core, implementations are typically registered in the
        container and managed by the container's lifecycle hooks.

    Resource Cleanup:
        Implementations MAY hold resources (connection pools, sockets).
        The creating code is responsible for cleanup. For ONEX patterns:
        - If registered in container, use container lifecycle hooks
        - If created locally, use async context managers if available
        - Never assume the protocol manages its own cleanup

        Example cleanup patterns:
            # Pattern 1: Container-managed (recommended)
            container.register_shutdown_hook(lambda: session.close())

            # Pattern 2: Context manager (local usage)
            async with aiohttp.ClientSession() as session:
                adapter = AioHttpClientAdapter(session)
                await use_adapter(adapter)

            # Pattern 3: Explicit cleanup (when necessary)
            try:
                adapter = create_adapter()
                await use_adapter(adapter)
            finally:
                await adapter.close()  # If implementation supports it

    Example implementation wrapper for aiohttp:
        # NOTE: This adapter implementation belongs in omnibase_infra, not omnibase_core.
        # Example location: omnibase_infra/adapters/http/aiohttp_client_adapter.py
        #
        # omnibase_core defines protocols only. Concrete implementations that depend
        # on external libraries (aiohttp, httpx, etc.) must live in omnibase_infra.

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

    Example with proper lifecycle:
        # Container registration (typical ONEX pattern)
        # Import adapter from omnibase_infra (NOT from omnibase_core):
        from omnibase_infra.adapters.http import AioHttpClientAdapter

        session = aiohttp.ClientSession()
        client = AioHttpClientAdapter(session)
        container.register_service("ProtocolHttpClient", client)

        # Later, during shutdown:
        await session.close()
    """

    # TODO(OMN-TBD): Add POST/HEAD/PUT methods if needed for advanced health checks  [NEEDS TICKET]
    # Current implementation intentionally minimal (YAGNI) - only GET is required.
    # Future use cases might include:
    #   - POST for stateful health checks
    #   - HEAD for lightweight pings
    #   - Custom methods for specialized endpoints
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
