# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HttpResponseContract — typed wire contract for HTTP responses.

This model represents the kernel's typed representation of an HTTP response,
forming the boundary between the handler implementation (e.g., ``HandlerHttp``)
and the kernel that inspects and logs the result of an HTTP call.

Design Principles:
    - Pure Pydantic model: zero imports from httpx, requests, or any handler/infra module.
    - Transport-agnostic: ``body`` is ``bytes``; callers decode as needed.
    - Stable SPI contract: all fields are stable interfaces — new optional fields
      may be added in minor versions only.

Use Cases:
    - Typed output from ``PrimitiveEffectExecutor.execute_http``
    - Request/response logging and observability (structured, not string-based)
    - Foundation for ``NodeHttpEffect`` and contract-level validation

See Also:
    - :class:`~omnibase_core.models.contracts.model_http_request_contract.HttpRequestContract`
    - OMN-4222: Defines HTTP wire contracts in omnibase_core

Thread Safety:
    ``HttpResponseContract`` is immutable (``frozen=True``) after creation, making it
    thread-safe for concurrent read access across threads or async tasks.

Stability Guarantee:
    - All fields, validators, and constructors are stable interfaces.
    - New optional fields may be added in minor versions only.
    - Existing fields cannot be removed or have types/constraints changed without
      a major version bump.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelHttpResponseContract"]


class ModelHttpResponseContract(BaseModel):
    """Typed wire contract for an inbound HTTP response.

    Represents the handler's typed model of an HTTP response, decoupled from any
    transport implementation. No httpx, requests, or handler imports are used —
    the model is pure Pydantic.

    Attributes:
        status_code: HTTP response status code (e.g., ``200``, ``404``, ``500``).
        headers: Response HTTP headers as a flat string-to-string mapping.
            Defaults to an empty dict if the response carries no headers.
        body: Raw response body as bytes.
            May be empty (``b""``) for responses with no body (e.g., 204 No Content).
            Callers are responsible for decoding based on the Content-Type header.
        elapsed_seconds: Time in seconds elapsed between sending the request and
            receiving the full response. ``None`` if not measured by the handler.

    Example:
        >>> resp = ModelHttpResponseContract(
        ...     status_code=200,
        ...     headers={"Content-Type": "application/json"},
        ...     body=b'{"result": "ok"}',
        ...     elapsed_seconds=0.123,
        ... )
        >>> resp.status_code
        200
        >>> resp.body
        b'{"result": "ok"}'
        >>> resp.elapsed_seconds
        0.123
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    status_code: int = Field(
        ...,
        description="HTTP response status code (e.g., 200, 201, 400, 404, 500).",
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Response HTTP headers as a flat string-to-string mapping. "
            "Keys are header names; values are header values."
        ),
    )
    body: bytes = Field(
        ...,
        description=(
            "Raw response body as bytes. "
            "May be empty (b'') for responses with no body (e.g., 204 No Content). "
            "Callers are responsible for decoding based on the Content-Type header."
        ),
    )
    elapsed_seconds: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Time in seconds elapsed between sending the request and receiving "
            "the full response. None if not measured by the handler."
        ),
    )
