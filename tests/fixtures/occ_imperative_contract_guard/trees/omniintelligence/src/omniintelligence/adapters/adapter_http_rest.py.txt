# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

# Copyright (c) 2025 OmniNode Team
"""HTTP/REST protocol handler.

Implements the ProtocolHandler interface for REST API interactions
using httpx as the async HTTP client.

Supported Operations:
    - GET: Retrieve resources
    - POST: Create resources
    - PUT: Update resources
    - DELETE: Remove resources

Config Keys:
    - base_url (str, required): Base URL for all requests
    - timeout (float, optional): Request timeout in seconds (default: 30.0)
    - headers (dict, optional): Default headers for all requests

Params Keys (per operation):
    - path (str, required): URL path appended to base_url
    - headers (dict, optional): Per-request headers (merged with defaults)
    - query_params (dict, optional): URL query parameters
    - body (dict, optional): JSON request body (POST/PUT)

Reference:
    - OMN-373: Protocol handlers for declarative effect nodes
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

# =============================================================================
# Logging
# =============================================================================

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

DEFAULT_TIMEOUT = 30.0
VALID_OPERATIONS = frozenset({"GET", "POST", "PUT", "DELETE"})


# =============================================================================
# Handler Implementation
# =============================================================================


class HttpRestHandler:
    """HTTP/REST protocol handler using httpx.

    Manages an async httpx client with connection pooling, configurable
    timeouts, and default headers. Supports GET, POST, PUT, DELETE.

    Thread Safety:
        httpx.AsyncClient is safe for concurrent use from multiple
        coroutines within the same event loop.
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._base_url: str = ""

    async def connect(self, config: dict[str, Any]) -> None:
        """Create an httpx AsyncClient with the given configuration.

        Args:
            config: Connection configuration.
                - base_url (str, required): Base URL for all requests.
                - timeout (float, optional): Request timeout in seconds.
                - headers (dict, optional): Default headers.

        Raises:
            ConnectionError: If base_url is missing.
        """
        base_url = config.get("base_url")
        if not base_url:
            raise ConnectionError("HttpRestHandler requires 'base_url' in config")

        timeout = config.get("timeout", DEFAULT_TIMEOUT)
        headers = config.get("headers", {})

        self._base_url = str(base_url).rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers=headers,
        )

        logger.info(
            "HTTP client connected",
            extra={"base_url": self._base_url},
        )

    async def execute(
        self,
        operation: str,
        params: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request.

        Args:
            operation: HTTP method (GET, POST, PUT, DELETE).
            params: Request parameters.
                - path (str, required): URL path.
                - headers (dict, optional): Per-request headers.
                - query_params (dict, optional): Query string parameters.
                - body (dict, optional): JSON body (POST/PUT).
            correlation_id: Optional correlation ID added as X-Correlation-ID header.

        Returns:
            dict with keys: status_code, headers, body.

        Raises:
            RuntimeError: If handler is not connected.
            ConnectionError: If the request fails due to connection issues.
            TimeoutError: If the request times out.
        """
        if self._client is None:
            raise RuntimeError(
                "HttpRestHandler is not connected. Call connect() first."
            )

        method = operation.upper()
        if method not in VALID_OPERATIONS:
            raise ValueError(
                f"Unsupported HTTP method: {method}. Must be one of {VALID_OPERATIONS}"
            )

        path = params.get("path", "/")
        headers = dict(params.get("headers", {}))
        query_params = params.get("query_params")
        body = params.get("body")

        if correlation_id:
            headers["X-Correlation-ID"] = correlation_id

        log_extra: dict[str, Any] = {
            "method": method,
            "path": path,
            "correlation_id": correlation_id,
        }

        try:
            response = await self._client.request(
                method=method,
                url=path,
                headers=headers if headers else None,
                params=query_params,
                json=body,
            )
        except httpx.ConnectError as exc:
            raise ConnectionError(f"HTTP connection failed: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"HTTP request timed out: {exc}") from exc

        logger.debug(
            "HTTP request completed",
            extra={**log_extra, "status_code": response.status_code},
        )

        # Build response body
        response_body: Any = None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                response_body = response.json()
            except Exception:
                response_body = response.text
        else:
            response_body = response.text

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_body,
        }

    async def disconnect(self) -> None:
        """Close the httpx client and release connections."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info(
                "HTTP client disconnected",
                extra={"base_url": self._base_url},
            )

    async def health_check(self) -> bool:
        """Check if the HTTP client is connected and operational.

        Returns:
            True if the client exists and is not closed.
        """
        if self._client is None:
            return False
        return not self._client.is_closed


__all__ = [
    "HttpRestHandler",
]
