"""
ModelPayloadHTTP - Typed payload for HTTP request intents.

This module provides the ModelPayloadHTTP model for outbound HTTP request
operations from Reducers. The Effect node receives the intent and
performs the HTTP request to the specified URL.

Design Pattern:
    Reducers emit this payload when an outbound HTTP request should be made.
    This separation ensures Reducer purity - the Reducer declares the
    desired outcome without performing the actual side effect.

Thread Safety:
    All payloads are immutable (frozen=True) after creation, making them
    thread-safe for concurrent read access.

Example:
    >>> from omnibase_core.models.reducer.payloads import ModelPayloadHTTP
    >>>
    >>> payload = ModelPayloadHTTP(
    ...     url="https://api.service.com/v1/notify",
    ...     method="POST",
    ...     headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
    ...     body={"event": "order.shipped", "order_id": "ORD-456"},
    ...     timeout_seconds=30,
    ...     retry_count=3,
    ... )

See Also:
    omnibase_core.models.reducer.payloads.ModelIntentPayloadBase: Base class
    omnibase_core.models.reducer.payloads.model_protocol_intent_payload: Protocol for intent payloads
"""

from typing import Literal

from pydantic import Field

from omnibase_core.models.reducer.payloads.model_intent_payload_base import (
    ModelIntentPayloadBase,
)

# Public API - listed immediately after imports per Python convention
__all__ = ["ModelPayloadHTTP"]


class ModelPayloadHTTP(ModelIntentPayloadBase):
    """Payload for HTTP request intents.

    Emitted by Reducers when an outbound HTTP request should be made.
    The Effect node executes this intent by performing the HTTP request
    to the specified URL with the given method, headers, and body.

    Supports all common HTTP methods and optional timeout/retry configuration.

    Attributes:
        intent_type: Discriminator literal for intent routing. Always "http_request".
            Placed first for optimal union type resolution performance.
        url: Target URL for the HTTP request.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH).
        headers: HTTP headers to include in the request.
        body: Request body. For JSON, pass a dict; for form data, pass encoded string.
        timeout_seconds: Request timeout in seconds.
        retry_count: Number of retries on failure (0 = no retries).
        follow_redirects: Whether to follow HTTP redirects.

    Example:
        >>> payload = ModelPayloadHTTP(
        ...     url="https://api.service.com/v1/notify",
        ...     method="POST",
        ...     headers={"Authorization": "Bearer token123", "Content-Type": "application/json"},
        ...     body={"event": "order.shipped", "order_id": "ORD-456"},
        ...     timeout_seconds=30,
        ...     retry_count=3,
        ... )
    """

    # NOTE: Discriminator field is placed FIRST for optimal union type resolution.
    intent_type: Literal["http_request"] = Field(
        default="http_request",
        description=(
            "Discriminator literal for intent routing. Used by Pydantic's "
            "discriminated union to dispatch to the correct Effect handler."
        ),
    )

    url: str = Field(
        ...,
        description=(
            "Target URL for the HTTP request. Must be a valid URL with scheme "
            "(http:// or https://)."
        ),
        min_length=1,
        max_length=2048,
    )

    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"] = Field(
        default="GET",
        description=(
            "HTTP method for the request. POST/PUT/PATCH typically include a body, "
            "GET/DELETE/HEAD typically do not."
        ),
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "HTTP headers to include in the request. Common headers: "
            "'Authorization', 'Content-Type', 'Accept', 'User-Agent'."
        ),
    )

    body: dict[str, object] | str | None = Field(
        default=None,
        description=(
            "Request body. For JSON APIs, pass a dict (will be serialized). "
            "For form data or raw content, pass a string."
        ),
    )

    query_params: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Query parameters to append to the URL. Will be URL-encoded "
            "and added to the request URL."
        ),
    )

    timeout_seconds: int = Field(
        default=30,
        description="Request timeout in seconds. After this time, the request fails.",
        ge=1,
        le=300,
    )

    retry_count: int = Field(
        default=0,
        description=(
            "Number of retries on failure. 0 means no retries. "
            "Retries use exponential backoff."
        ),
        ge=0,
        le=10,
    )

    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow HTTP 3xx redirects automatically.",
    )
