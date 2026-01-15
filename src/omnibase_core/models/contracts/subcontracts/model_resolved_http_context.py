"""
Resolved HTTP Context Model for NodeEffect Handler Contract.

This model represents a resolved (template-free) HTTP context that handlers receive
after template resolution by the effect executor.

Thread Safety:
    This model is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

See Also:
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType


class ModelResolvedHttpContext(BaseModel):
    """
    Resolved HTTP context for API calls and webhooks.

    All template placeholders have been resolved by the effect executor.
    The handler receives fully-resolved values ready for execution.

    Attributes:
        handler_type: Discriminator field for HTTP handler type.
        url: Fully resolved URL (no template placeholders).
        method: HTTP method for the request (GET, POST, PUT, PATCH, DELETE).
        headers: Resolved HTTP headers (all template values substituted).
        body: Resolved request body (None for GET requests).
        query_params: Resolved query parameters.
        timeout_ms: Request timeout in milliseconds (1s - 10min).
        follow_redirects: Whether to follow HTTP redirects.
        verify_ssl: Whether to verify SSL certificates.

    Example resolved values:
        - url: "https://api.example.com/users/123" (was: "${API_BASE}/users/${user_id}")
        - headers: {"Authorization": "Bearer abc123"} (was: {"Authorization": "Bearer ${API_TOKEN}"})
    """

    handler_type: Literal[EnumEffectHandlerType.HTTP] = Field(
        default=EnumEffectHandlerType.HTTP,
        description="Handler type discriminator for HTTP operations",
    )

    url: str = Field(
        ...,
        min_length=1,
        description="Fully resolved URL (no template placeholders)",
    )

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(
        ...,
        description="HTTP method for the request",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved HTTP headers (all template values substituted)",
    )

    body: str | None = Field(
        default=None,
        description="Resolved request body (None for GET requests)",
    )

    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Resolved query parameters",
    )

    # Timeout bounds: 1s minimum (realistic production I/O), 10min maximum
    # Matches IO config timeout bounds for consistency across the effect layer
    timeout_ms: int = Field(
        default=EFFECT_TIMEOUT_DEFAULT_MS,
        ge=EFFECT_TIMEOUT_MIN_MS,
        le=EFFECT_TIMEOUT_MAX_MS,
        description="Request timeout in milliseconds (1s - 10min)",
    )

    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow HTTP redirects",
    )

    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )
