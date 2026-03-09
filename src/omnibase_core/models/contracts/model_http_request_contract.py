# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HttpRequestContract — typed wire contract for HTTP requests.

This model represents the kernel's typed representation of an HTTP request,
forming the boundary between the kernel's notion of an HTTP call and the
handler implementation that performs it (e.g., ``HandlerHttp`` via
``PrimitiveEffectExecutor.execute_http``).

Design Principles:
    - Pure Pydantic model: zero imports from httpx, requests, or any handler/infra module.
    - Transport-agnostic: ``body`` is ``bytes``; callers decode as needed.
    - Stable SPI contract: all fields are stable interfaces — new optional fields
      may be added in minor versions only.

Use Cases:
    - Typed input to ``PrimitiveEffectExecutor.execute_http``
    - Request/response logging and observability (structured, not string-based)
    - Foundation for ``NodeHttpEffect`` and contract-level validation

See Also:
    - :class:`~omnibase_core.models.contracts.model_http_response_contract.HttpResponseContract`
    - OMN-4222: Defines HTTP wire contracts in omnibase_core

Thread Safety:
    ``HttpRequestContract`` is immutable (``frozen=True``) after creation, making it
    thread-safe for concurrent read access across threads or async tasks.

Stability Guarantee:
    - All fields, validators, and constructors are stable interfaces.
    - New optional fields may be added in minor versions only.
    - Existing fields cannot be removed or have types/constraints changed without
      a major version bump.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelHttpRequestContract"]


class ModelHttpRequestContract(BaseModel):
    """Typed wire contract for an outbound HTTP request.

    Represents the kernel's typed model of an HTTP call, decoupled from any
    handler or transport implementation. No httpx, requests, or handler imports
    are used — the model is pure Pydantic.

    Attributes:
        method: HTTP method in uppercase (e.g., ``"GET"``, ``"POST"``).
        url: Fully-qualified target URL including scheme and path.
        headers: Optional HTTP headers as a flat string-to-string mapping.
            Keys are header names; values are header values.
            Defaults to an empty dict (no headers).
        body: Optional raw request body as bytes.
            ``None`` for requests that carry no body (e.g., GET, DELETE).
        timeout_seconds: Maximum time in seconds to wait for a response.
            Defaults to ``30.0`` seconds.
        follow_redirects: Whether the handler should follow HTTP redirects.
            Defaults to ``True``.

    Example:
        >>> req = ModelHttpRequestContract(
        ...     method="POST",
        ...     url="https://api.example.com/v1/nodes",
        ...     headers={"Content-Type": "application/json"},
        ...     body=b'{"node_id": "abc"}',
        ... )
        >>> req.method
        'POST'
        >>> req.timeout_seconds
        30.0
        >>> req.follow_redirects
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    method: str = Field(
        ...,
        description=(
            "HTTP method in uppercase. "
            "Expected values: 'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'."
        ),
    )
    url: str = Field(
        ...,
        description="Fully-qualified target URL including scheme, host, and path.",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "HTTP headers as a flat string-to-string mapping. "
            "Keys are header names; values are header values."
        ),
    )
    body: bytes | None = Field(
        default=None,
        description=(
            "Raw request body as bytes. "
            "None for requests that carry no body (e.g., GET, DELETE). "
            "Callers are responsible for encoding and content-type negotiation."
        ),
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Maximum time in seconds to wait for a response. Must be positive.",
    )
    follow_redirects: bool = Field(
        default=True,
        description="Whether the handler should follow HTTP redirects.",
    )
