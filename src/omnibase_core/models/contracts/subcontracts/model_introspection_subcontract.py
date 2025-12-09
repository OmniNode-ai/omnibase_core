"""
Introspection Subcontract Model.



Dedicated subcontract model for introspection functionality providing:
- Node metadata exposure and discovery
- Contract information retrieval
- Capability introspection
- Schema export and validation
- Runtime introspection depth control
- Field filtering and exclusion

This model is composed into node contracts that require introspection functionality,
providing clean separation between node logic and introspection behavior.

Strict typing is enforced: No Any types allowed in implementation.
"""

from typing import ClassVar, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelIntrospectionSubcontract(BaseModel):
    """
    Introspection subcontract model for node discovery and metadata exposure.

    Provides standardized introspection capabilities for ONEX nodes including
    metadata exposure, contract retrieval, capability discovery, and schema export.
    Designed for composition into node contracts requiring introspection functionality.

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )

    # Correlation and tracing
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for introspection operations",
    )

    # Core introspection configuration
    introspection_enabled: bool = Field(
        default=True,
        description="Enable introspection functionality",
    )

    # Metadata inclusion controls
    include_metadata: bool = Field(
        default=True,
        description="Include node metadata in introspection response",
    )

    include_core_metadata: bool = Field(
        default=True,
        description="Include core metadata (name, version, type)",
    )

    include_organization_metadata: bool = Field(
        default=True,
        description="Include organization metadata (author, description, tags)",
    )

    # Contract and schema inclusion
    include_contract: bool = Field(
        default=True,
        description="Include contract details in introspection response",
    )

    include_input_schema: bool = Field(
        default=True,
        description="Include input state schema in introspection response",
    )

    include_output_schema: bool = Field(
        default=True,
        description="Include output state schema in introspection response",
    )

    include_cli_interface: bool = Field(
        default=True,
        description="Include CLI interface details in introspection response",
    )

    # Capability and dependency information
    include_capabilities: bool = Field(
        default=True,
        description="Include node capabilities in introspection response",
    )

    include_dependencies: bool = Field(
        default=True,
        description="Include runtime dependencies in introspection response",
    )

    include_optional_dependencies: bool = Field(
        default=True,
        description="Include optional dependencies in introspection response",
    )

    include_external_tools: bool = Field(
        default=True,
        description="Include external tool dependencies in introspection response",
    )

    # State and error information
    include_state_models: bool = Field(
        default=True,
        description="Include state model information in introspection response",
    )

    include_error_codes: bool = Field(
        default=True,
        description="Include error codes in introspection response",
    )

    include_event_channels: bool = Field(
        default=True,
        description="Include event channels in introspection response",
    )

    # Depth and filtering controls
    depth_limit: int = Field(
        default=10,
        description="Maximum introspection depth for nested objects",
        ge=1,
        le=50,
    )

    exclude_fields: list[str] = Field(
        default_factory=list,
        description="Fields to exclude from introspection response",
    )

    exclude_field_patterns: list[str] = Field(
        default_factory=lambda: [
            "password",
            "secret",
            "token",
            "api_key",
            "private_key",
            "credential",
        ],
        description="Field name patterns to exclude from introspection (security)",
    )

    # Schema export configuration
    export_json_schema: bool = Field(
        default=True,
        description="Export JSON schema for input/output models",
    )

    export_openapi_schema: bool = Field(
        default=False,
        description="Export OpenAPI schema for API endpoints",
    )

    # Performance and caching
    cache_introspection_response: bool = Field(
        default=True,
        description="Cache introspection response for performance",
    )

    cache_ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cached introspection response",
        ge=60,
        le=3600,
    )

    # Output format controls
    compact_output: bool = Field(
        default=False,
        description="Use compact JSON output (no indentation)",
    )

    include_timestamps: bool = Field(
        default=True,
        description="Include timestamps in introspection response",
    )

    include_version_info: bool = Field(
        default=True,
        description="Include version information (protocol, schema, node)",
    )

    # Discovery and registration
    enable_auto_discovery: bool = Field(
        default=True,
        description="Enable automatic discovery by registry services",
    )

    enable_health_check: bool = Field(
        default=True,
        description="Include health check endpoint in introspection",
    )

    enable_lifecycle_hooks: bool = Field(
        default=True,
        description="Include lifecycle hook information in introspection",
    )

    # Security and privacy
    redact_sensitive_info: bool = Field(
        default=True,
        description="Automatically redact sensitive information from introspection",
    )

    require_authentication: bool = Field(
        default=False,
        description="Require authentication for introspection endpoint",
    )

    allowed_introspection_sources: list[str] = Field(
        default_factory=list,
        description="Allowed IP addresses or sources for introspection requests",
    )

    @model_validator(mode="after")
    def validate_depth_limit(self) -> Self:
        """Validate depth limit is within reasonable bounds."""
        if self.depth_limit > 30:
            msg = (
                "depth_limit exceeding 30 may cause performance issues; "
                "consider using a lower depth limit for better performance"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "recommended_max_value": ModelSchemaValue.from_value(30),
                        "provided_value": ModelSchemaValue.from_value(self.depth_limit),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_cache_ttl(self) -> Self:
        """Validate cache TTL is reasonable."""
        if self.cache_introspection_response and self.cache_ttl_seconds < 60:
            msg = (
                "cache_ttl_seconds below 60 seconds may cause excessive cache churn; "
                "consider using a longer TTL for better performance"
            )
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "minimum_recommended_value": ModelSchemaValue.from_value(60),
                        "provided_value": ModelSchemaValue.from_value(
                            self.cache_ttl_seconds
                        ),
                    },
                ),
            )
        return self

    @model_validator(mode="after")
    def validate_introspection_consistency(self) -> Self:
        """Validate introspection configuration is internally consistent."""
        # If introspection is disabled, warn about enabled sub-features
        if not self.introspection_enabled:
            enabled_features = []
            if self.include_metadata:
                enabled_features.append("include_metadata")
            if self.include_contract:
                enabled_features.append("include_contract")
            if self.include_capabilities:
                enabled_features.append("include_capabilities")

            if enabled_features:
                msg = (
                    f"introspection_enabled is False, but the following features are enabled: "
                    f"{', '.join(enabled_features)}. These features will have no effect."
                )
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                            "enabled_features": ModelSchemaValue.from_value(
                                enabled_features
                            ),
                        },
                    ),
                )

        # If caching is disabled but TTL is set, it's a no-op (just a warning scenario)
        # We don't need to raise an error for this, as it's harmless

        return self

    @model_validator(mode="after")
    def validate_security_consistency(self) -> Self:
        """Validate security configuration is consistent."""
        # If authentication is required, we should have allowed sources or it's open
        if self.require_authentication and not self.allowed_introspection_sources:
            # This is actually fine - authentication can be handled at a higher level
            # Just ensure redaction is enabled for safety
            if not self.redact_sensitive_info:
                msg = (
                    "require_authentication is True but redact_sensitive_info is False. "
                    "This may expose sensitive information. Consider enabling redaction."
                )
                raise ModelOnexError(
                    message=msg,
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    details=ModelErrorContext.with_context(
                        {
                            "error_type": ModelSchemaValue.from_value("valueerror"),
                            "validation_context": ModelSchemaValue.from_value(
                                "model_validation",
                            ),
                            "security_risk": ModelSchemaValue.from_value(
                                "sensitive_data_exposure"
                            ),
                        },
                    ),
                )

        return self
