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
    The following example shows the complete integration pattern for
    registering an HTTP client with the ONEX DI container.

    IMPORTANT: Adapter implementations belong in omnibase_infra, NOT omnibase_core.
    omnibase_core defines protocols (interfaces) only. Concrete implementations
    that depend on external libraries (aiohttp, httpx, etc.) must live in the
    infrastructure layer to maintain clean architecture boundaries.

    Step 1: Create an adapter implementation (in omnibase_infra)
        # NOTE: This adapter implementation belongs in omnibase_infra, not omnibase_core.
        # Example location: omnibase_infra/adapters/http/aiohttp_client_adapter.py
        import aiohttp
        from typing import Any
        from omnibase_core.protocols.http import (
            ProtocolHttpClient,
            ProtocolHttpResponse,
        )

        class AioHttpResponseAdapter:
            '''Adapts aiohttp response to ProtocolHttpResponse.'''

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
            '''Adapts aiohttp.ClientSession to ProtocolHttpClient.'''

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

    Step 2: Register with the DI container
        # application/bootstrap.py
        import aiohttp
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )
        # Import adapter from omnibase_infra (NOT from omnibase_core):
        from omnibase_infra.adapters.http import AioHttpClientAdapter

        async def setup_container() -> ModelONEXContainer:
            container = ModelONEXContainer()

            # Create session (will be cleaned up on shutdown)
            session = aiohttp.ClientSession()
            adapter = AioHttpClientAdapter(session)

            # Register using protocol name as key
            container.register_service("ProtocolHttpClient", adapter)

            # Register cleanup hook for graceful shutdown
            container.register_shutdown_hook(
                lambda: session.close()
            )

            return container

    Step 3: Inject into nodes
        # nodes/node_my_service_effect.py
        from omnibase_core.nodes import NodeEffect
        from omnibase_core.models.container.model_onex_container import (
            ModelONEXContainer,
        )
        from omnibase_core.protocols.http import ProtocolHttpClient

        class NodeMyServiceEffect(NodeEffect):
            def __init__(self, container: ModelONEXContainer):
                super().__init__(container)
                # Get HTTP client via protocol-based DI
                self.http_client: ProtocolHttpClient = container.get_service(
                    "ProtocolHttpClient"
                )
                self.health_url = "http://service/health"

            async def execute_effect(self) -> ModelEffectOutput:
                try:
                    response = await self.http_client.get(
                        self.health_url,
                        timeout=5.0
                    )
                    return ModelEffectOutput(
                        success=response.status == 200,
                        data={"status_code": response.status}
                    )
                except (ConnectionError, TimeoutError) as e:
                    return ModelEffectOutput(
                        success=False,
                        error=str(e)
                    )

Testing with Mocks:
    The protocol-based approach makes testing straightforward:

        # tests/test_node_my_service_effect.py
        import pytest
        from unittest.mock import Mock, AsyncMock

        @pytest.fixture
        def mock_http_client() -> ProtocolHttpClient:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="OK")
            mock_response.json = AsyncMock(return_value={"status": "healthy"})

            client = Mock()
            client.get = AsyncMock(return_value=mock_response)
            return client

        @pytest.fixture
        def container_with_mock(mock_http_client) -> ModelONEXContainer:
            container = ModelONEXContainer()
            container.register_service("ProtocolHttpClient", mock_http_client)
            return container

        async def test_health_check_success(container_with_mock):
            node = NodeMyServiceEffect(container_with_mock)
            result = await node.execute_effect()
            assert result.success is True

    See protocol_http_client.py for complete migration guide and
    lifecycle management patterns.
"""

from omnibase_core.protocols.http.protocol_http_client import (
    ProtocolHttpClient,
    ProtocolHttpResponse,
)

__all__ = [
    "ProtocolHttpClient",
    "ProtocolHttpResponse",
]
