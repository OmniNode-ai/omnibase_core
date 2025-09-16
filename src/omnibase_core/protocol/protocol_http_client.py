"""
ONEX HTTP Client Protocol

This protocol defines the interface for HTTP client implementations in the ONEX architecture.
Used by EFFECT nodes that need to make external HTTP requests, particularly for webhook
and notification systems.

Security Note: Implementations must include SSRF protection and validate all target URLs.
"""

from typing import Any, Dict, Optional, Protocol

from pydantic import BaseModel


class ModelHttpResponse(BaseModel):
    """Response model for HTTP requests."""

    status_code: int
    headers: Dict[str, str]
    body: bytes

    class Config:
        """Pydantic configuration."""

        frozen = True
        extra = "forbid"


class ProtocolHttpClient(Protocol):
    """
    Protocol for HTTP client implementations.

    This protocol defines the standard interface for making HTTP requests in ONEX.
    Implementations must provide robust error handling, timeout management,
    and security validation.

    Security Requirements:
    - Must validate URLs to prevent SSRF attacks
    - Must implement proper timeout handling
    - Must sanitize headers and request data
    - Should implement circuit breaker patterns for resilience
    """

    async def request(
        self,
        method: str,
        url: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = 10.0,
    ) -> ModelHttpResponse:
        """
        Make an HTTP request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            url: Target URL for the request
            json: Optional JSON payload for the request body
            headers: Optional HTTP headers to include
            timeout: Request timeout in seconds (default: 10.0)

        Returns:
            ModelHttpResponse: Response containing status, headers, and body

        Raises:
            OnexError: For any HTTP client errors, network issues, or security violations

        Security Notes:
        - URL must be validated to prevent SSRF attacks
        - Timeout must be enforced to prevent resource exhaustion
        - Headers must be sanitized to prevent injection attacks
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if the HTTP client is healthy and operational.

        Returns:
            bool: True if the client is healthy, False otherwise
        """
        ...

    async def close(self) -> None:
        """
        Clean up and close the HTTP client.

        This method should be called when the client is no longer needed
        to properly release resources and close connections.
        """
        ...
