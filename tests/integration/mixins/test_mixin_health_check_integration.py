# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration tests for check_http_service_health with real HTTP adapters.

These tests verify that the ProtocolHttpClient and ProtocolHttpResponse protocols
work correctly with adapter implementations, ensuring the abstractions are sound.
"""

from typing import Any

import pytest

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


# =============================================================================
# Adapter implementations for testing
# =============================================================================


class AioHttpResponseAdapter:
    """Adapter implementing ProtocolHttpResponse for testing.

    This adapter wraps response data and implements the protocol interface.
    In production, this would wrap an actual aiohttp.ClientResponse.

    Example production implementation:
        class AioHttpResponseAdapter:
            def __init__(self, response: aiohttp.ClientResponse):
                self._response = response

            @property
            def status(self) -> int:
                return self._response.status

            async def text(self) -> str:
                return await self._response.text()

            async def json(self) -> Any:
                return await self._response.json()
    """

    def __init__(
        self,
        status: int,
        text_content: str = "",
        json_content: Any = None,
    ) -> None:
        """Initialize the response adapter.

        Args:
            status: HTTP status code
            text_content: Response body as text
            json_content: Response body as parsed JSON
        """
        self._status = status
        self._text = text_content
        self._json = json_content if json_content is not None else {}

    @property
    def status(self) -> int:
        """HTTP status code of the response."""
        return self._status

    async def text(self) -> str:
        """Get the response body as text."""
        return self._text

    async def json(self) -> Any:
        """Parse the response body as JSON."""
        return self._json


class AioHttpClientAdapter:
    """Adapter implementing ProtocolHttpClient for testing.

    This adapter provides configurable responses for different URLs,
    enabling comprehensive testing without actual HTTP calls.

    Example production implementation:
        class AioHttpClientAdapter:
            def __init__(self, session: aiohttp.ClientSession):
                self._session = session

            async def get(
                self,
                url: str,
                timeout: float | None = None,
                headers: dict[str, str] | None = None,
            ) -> AioHttpResponseAdapter:
                client_timeout = aiohttp.ClientTimeout(total=timeout)
                async with self._session.get(
                    url, timeout=client_timeout, headers=headers
                ) as response:
                    return AioHttpResponseAdapter(response)
    """

    def __init__(
        self,
        responses: dict[str, AioHttpResponseAdapter] | None = None,
        default_exception: Exception | None = None,
    ) -> None:
        """Initialize the client adapter.

        Args:
            responses: Mapping of URL to response adapter
            default_exception: Exception to raise for unconfigured URLs
        """
        self._responses = responses or {}
        self._default_exception = default_exception

    async def get(
        self,
        url: str,
        timeout: float | None = None,
        headers: dict[str, str] | None = None,
    ) -> AioHttpResponseAdapter:
        """Perform HTTP GET request.

        Args:
            url: The URL to request
            timeout: Optional timeout in seconds
            headers: Optional HTTP headers

        Returns:
            Response adapter with configured response

        Raises:
            ConnectionError: If URL not configured and no default exception
            Exception: If default_exception is set
        """
        if url in self._responses:
            return self._responses[url]
        if self._default_exception:
            raise self._default_exception
        raise ConnectionError(f"No mock response configured for {url}")


# =============================================================================
# Integration tests
# =============================================================================


class TestCheckHttpServiceHealthIntegration:
    """Integration tests for check_http_service_health with adapters."""

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_adapter_implements_protocol_http_response(self) -> None:
        """Test that AioHttpResponseAdapter implements ProtocolHttpResponse."""
        from omnibase_core.protocols.http import ProtocolHttpResponse

        response = AioHttpResponseAdapter(status=200)

        # Verify protocol compliance via isinstance (runtime_checkable)
        assert isinstance(response, ProtocolHttpResponse)
        assert response.status == 200

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_adapter_implements_protocol_http_client(self) -> None:
        """Test that AioHttpClientAdapter implements ProtocolHttpClient."""
        from omnibase_core.protocols.http import ProtocolHttpClient

        client = AioHttpClientAdapter()

        # Verify protocol compliance via isinstance (runtime_checkable)
        assert isinstance(client, ProtocolHttpClient)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_adapter_response_text_and_json_methods(self) -> None:
        """Test that response adapter text() and json() methods work."""
        response = AioHttpResponseAdapter(
            status=200,
            text_content='{"status": "ok"}',
            json_content={"status": "ok"},
        )

        text = await response.text()
        json_data = await response.json()

        assert text == '{"status": "ok"}'
        assert json_data == {"status": "ok"}

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_check_health_with_adapter_healthy(self) -> None:
        """Test check_http_service_health returns healthy with 200 response."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        response = AioHttpResponseAdapter(status=200)
        client = AioHttpClientAdapter(responses={"http://test.com/health": response})

        result = await check_http_service_health(
            "http://test.com",
            http_client=client,
        )

        assert result.status == "healthy"
        assert result.health_score == 1.0
        assert len(result.issues) == 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_check_health_with_adapter_degraded_status(self) -> None:
        """Test check_http_service_health returns degraded for non-200 response."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        response = AioHttpResponseAdapter(status=503)
        client = AioHttpClientAdapter(responses={"http://test.com/health": response})

        result = await check_http_service_health(
            "http://test.com",
            expected_status=200,
            http_client=client,
        )

        assert result.status == "degraded"
        assert len(result.issues) > 0
        assert any("503" in issue.message for issue in result.issues)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_check_health_with_adapter_custom_expected_status(self) -> None:
        """Test check_http_service_health with custom expected status."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        response = AioHttpResponseAdapter(status=204)
        client = AioHttpClientAdapter(responses={"http://test.com/health": response})

        result = await check_http_service_health(
            "http://test.com",
            expected_status=204,
            http_client=client,
        )

        assert result.status == "healthy"
        assert result.health_score == 1.0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_check_health_with_adapter_timeout(self) -> None:
        """Test check_http_service_health handles timeout errors."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        client = AioHttpClientAdapter(default_exception=TimeoutError("timed out"))

        result = await check_http_service_health(
            "http://test.com",
            http_client=client,
        )

        assert result.status == "degraded"
        assert len(result.issues) > 0
        assert any("timed out" in issue.message for issue in result.issues)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_check_health_with_adapter_connection_error(self) -> None:
        """Test check_http_service_health handles connection errors."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        client = AioHttpClientAdapter(
            default_exception=ConnectionError("connection refused")
        )

        result = await check_http_service_health(
            "http://test.com",
            http_client=client,
        )

        assert result.status == "unhealthy"
        assert result.health_score == 0.0
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_check_health_with_adapter_url_health_appending(self) -> None:
        """Test that /health is appended to URLs without it."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        # Configure response for the /health URL
        response = AioHttpResponseAdapter(status=200)
        client = AioHttpClientAdapter(responses={"http://test.com/health": response})

        result = await check_http_service_health(
            "http://test.com",  # No /health suffix
            http_client=client,
        )

        # Should succeed because /health was appended
        assert result.status == "healthy"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_check_health_with_adapter_preserves_health_suffix(self) -> None:
        """Test that /health is not doubled if already present."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        # Configure response for the /health URL
        response = AioHttpResponseAdapter(status=200)
        client = AioHttpClientAdapter(responses={"http://test.com/health": response})

        result = await check_http_service_health(
            "http://test.com/health",  # Already has /health
            http_client=client,
        )

        # Should succeed (not try /health/health)
        assert result.status == "healthy"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)
    async def test_adapter_client_with_multiple_urls(self) -> None:
        """Test that client can handle multiple URL configurations."""
        from omnibase_core.mixins.mixin_health_check import check_http_service_health

        responses = {
            "http://service1.com/health": AioHttpResponseAdapter(status=200),
            "http://service2.com/health": AioHttpResponseAdapter(status=503),
        }
        client = AioHttpClientAdapter(responses=responses)

        result1 = await check_http_service_health(
            "http://service1.com",
            http_client=client,
        )
        result2 = await check_http_service_health(
            "http://service2.com",
            http_client=client,
        )

        assert result1.status == "healthy"
        assert result2.status == "degraded"
