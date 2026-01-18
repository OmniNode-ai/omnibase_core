"""
HTTP IO Configuration Model.

Handler-specific IO configuration for REST API calls using Pydantic models.
Provides URL templating with ${} placeholders, HTTP method configuration,
headers, body templates, query parameters, and connection settings.

ZERO TOLERANCE: No Any types allowed in implementation.

Thread Safety:
    This IO configuration model is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.

See Also:
    - :class:`ModelEffectSubcontract`: Parent contract using these IO configs
    - :mod:`omnibase_core.models.contracts.subcontracts.model_effect_resolved_context`:
        Resolved context models after template substitution
    - :class:`NodeEffect`: The primary node using these configurations
    - docs/architecture/CONTRACT_DRIVEN_NODEEFFECT_V1_0.md: Full specification
    - examples/contracts/effect/: Example YAML contracts

Author: ONEX Framework Team
"""

import warnings
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.constants.constants_effect_limits import (
    EFFECT_TIMEOUT_DEFAULT_MS,
    EFFECT_TIMEOUT_MAX_MS,
    EFFECT_TIMEOUT_MIN_MS,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_effect_handler_type import EnumEffectHandlerType
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

__all__ = [
    "ModelHttpIOConfig",
]


class ModelHttpIOConfig(BaseModel):
    """
    HTTP IO configuration for REST API calls.

    Provides URL templating with ${} placeholders, HTTP method configuration,
    headers, body templates, query parameters, and connection settings.

    Attributes:
        handler_type: Discriminator field identifying this as an HTTP handler.
        url_template: URL with ${} placeholders for variable substitution.
        method: HTTP method (GET, POST, PUT, PATCH, DELETE).
        headers: HTTP headers with optional ${} placeholders.
        body_template: Request body template with ${} placeholders.
        query_params: Query parameters with optional ${} placeholders.
        timeout_ms: Request timeout in milliseconds (1s - 10min).
        follow_redirects: Whether to follow HTTP redirects.
        verify_ssl: Whether to verify SSL certificates.

    Example:
        >>> config = ModelHttpIOConfig(
        ...     url_template="https://api.example.com/users/${input.user_id}",
        ...     method="GET",
        ...     headers={"Authorization": "Bearer ${env.API_TOKEN}"},
        ...     timeout_ms=5000,
        ... )
    """

    handler_type: Literal[EnumEffectHandlerType.HTTP] = Field(
        default=EnumEffectHandlerType.HTTP,
        description="Discriminator field for HTTP handler",
    )

    url_template: str = Field(
        ...,
        description="URL with ${} placeholders for variable substitution",
        min_length=1,
    )

    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = Field(
        ...,
        description="HTTP method for the request",
    )

    headers: dict[str, str] = Field(
        default_factory=dict,
        description="HTTP headers with optional ${} placeholders",
    )

    body_template: str | None = Field(
        default=None,
        description="Request body template with ${} placeholders (required for POST/PUT/PATCH)",
    )

    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameters with optional ${} placeholders",
    )

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

    @field_validator("verify_ssl", mode="after")
    @classmethod
    def warn_on_disabled_ssl_verification(cls, value: bool) -> bool:
        """
        Emit a security warning when SSL verification is disabled.

        Args:
            value: The verify_ssl field value.

        Returns:
            The unchanged value after emitting warning if False.
        """
        if not value:
            warnings.warn(
                "verify_ssl=False disables SSL certificate validation. "
                "This is insecure for production use.",
                UserWarning,
                stacklevel=2,
            )
        return value

    @model_validator(mode="after")
    def validate_body_for_method(self) -> "ModelHttpIOConfig":
        """
        Require body_template for POST/PUT/PATCH methods.

        These HTTP methods typically carry a request body, so a body_template
        is required to ensure the request is properly configured.

        Returns:
            The validated model instance.

        Raises:
            ModelOnexError: If body_template is None for POST/PUT/PATCH.
        """
        methods_requiring_body = {"POST", "PUT", "PATCH"}
        if self.method in methods_requiring_body and self.body_template is None:
            raise ModelOnexError(
                message=f"body_template is required for {self.method} requests",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation"
                        ),
                        "method": ModelSchemaValue.from_value(self.method),
                    }
                ),
            )
        return self

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)
