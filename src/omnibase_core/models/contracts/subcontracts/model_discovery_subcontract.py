"""
Discovery Subcontract Model.



Dedicated subcontract model for service discovery functionality providing:
- Discovery responder configuration and lifecycle management
- Broadcast response handling with rate limiting
- Capability advertisement and metadata management
- Discovery channel configuration for event bus routing
- Health status and introspection integration
- Response throttling and performance tuning

This model is composed into node contracts that require service discovery functionality,
enabling nodes to participate in ONEX discovery broadcasts and respond with introspection
data, health status, and capabilities.

Strict typing is enforced: No Any types allowed in implementation.

MIXIN INTEGRATION:
- Designed for use with MixinDiscoveryResponder
- Provides declarative configuration for discovery behavior
- Enables YAML-based discovery setup without code changes
"""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelDiscoverySubcontract(BaseModel):
    """
    Discovery Subcontract for service discovery and introspection.

    Comprehensive discovery configuration providing discovery response behavior,
    rate limiting, capability advertisement, and event bus integration. Designed
    for composition into node contracts requiring service discovery participation.

    DISCOVERY RESPONDER PATTERN:
    - All nodes listen to 'onex.discovery.broadcast' channel
    - Respond to DISCOVERY_REQUEST events with introspection data
    - Include health status, capabilities, and full introspection
    - Rate limiting prevents discovery spam

    CONFIGURATION FIELDS:
    - enabled: Enable/disable discovery responder functionality
    - response_throttle_seconds: Minimum time between discovery responses
    - response_timeout_seconds: Maximum time allowed for response generation
    - advertise_capabilities: Whether to include capability list in responses
    - discovery_channels: Event bus channels for discovery communication
    - default_health_status: Fallback health status when checks unavailable
    - include_introspection: Whether to include full node introspection
    - include_event_channels: Whether to include event channel information
    - filter_enabled: Enable custom discovery request filtering
    - auto_start: Automatically start discovery responder on node initialization

    THREAD SAFETY:
    ⚠️ Configuration is immutable after initialization (Pydantic frozen=False by default)
    ⚠️ Discovery state managed by MixinDiscoveryResponder (see threading docs)

    Strict typing is enforced: No Any types allowed in implementation.
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    # Core discovery configuration
    enabled: bool = Field(
        default=True,
        description="Enable discovery responder functionality",
    )

    auto_start: bool = Field(
        default=True,
        description="Automatically start discovery responder on node initialization",
    )

    # Rate limiting and throttling
    response_throttle_seconds: float = Field(
        default=1.0,
        description="Minimum seconds between discovery responses (rate limiting)",
        ge=0.1,
        le=300.0,
    )

    response_timeout_seconds: float = Field(
        default=5.0,
        description="Maximum time allowed to generate and send discovery response",
        ge=0.5,
        le=60.0,
    )

    # Capability advertisement
    advertise_capabilities: bool = Field(
        default=True,
        description="Include node capabilities in discovery responses",
    )

    custom_capabilities: list[str] = Field(
        default_factory=list,
        description="Additional custom capabilities to advertise (beyond auto-detected)",
    )

    # Event bus integration
    discovery_channels: list[str] = Field(
        default_factory=lambda: [
            "onex.discovery.broadcast",
            "onex.discovery.response",
        ],
        description="Event bus channels for discovery communication",
    )

    use_dedicated_consumer_group: bool = Field(
        default=True,
        description="Use node-specific consumer group for discovery broadcasts",
    )

    # Response content configuration
    include_introspection: bool = Field(
        default=True,
        description="Include full node introspection data in responses",
    )

    include_event_channels: bool = Field(
        default=True,
        description="Include event channel information in responses",
    )

    include_version_info: bool = Field(
        default=True,
        description="Include node version information in responses",
    )

    include_health_status: bool = Field(
        default=True,
        description="Include current health status in responses",
    )

    # Health status configuration
    default_health_status: str = Field(
        default="healthy",
        description="Default health status when health checks unavailable",
    )

    enable_health_checks: bool = Field(
        default=True,
        description="Enable health checks for discovery responses",
    )

    # Filtering and matching
    filter_enabled: bool = Field(
        default=True,
        description="Enable custom discovery request filtering",
    )

    match_node_types: list[str] = Field(
        default_factory=list,
        description="Node types to match in discovery requests (empty = match all)",
    )

    required_capabilities_filter: list[str] = Field(
        default_factory=list,
        description="Only respond if request requires these capabilities",
    )

    # Monitoring and metrics
    enable_metrics: bool = Field(
        default=True,
        description="Enable discovery response metrics collection",
    )

    enable_detailed_logging: bool = Field(
        default=False,
        description="Enable detailed logging for discovery operations",
    )

    log_throttled_requests: bool = Field(
        default=False,
        description="Log requests that were throttled (can be noisy)",
    )

    log_filtered_requests: bool = Field(
        default=False,
        description="Log requests that were filtered out (can be noisy)",
    )

    # Performance tuning
    max_response_size_bytes: int = Field(
        default=102400,  # 100 KB
        description="Maximum size of discovery response in bytes",
        ge=1024,
        le=1048576,  # 1 MB max
    )

    enable_response_compression: bool = Field(
        default=False,
        description="Enable response compression for large payloads",
    )

    # Error handling
    ignore_invalid_requests: bool = Field(
        default=True,
        description="Silently ignore invalid discovery requests instead of logging errors",
    )

    max_error_count_before_disable: int = Field(
        default=100,
        description="Disable discovery responder after this many consecutive errors",
        ge=10,
        le=1000,
    )

    @model_validator(mode="after")
    def validate_discovery_configuration(self) -> "ModelDiscoverySubcontract":
        """Validate discovery configuration fields after model construction."""
        # Validate default_health_status
        allowed_health_statuses = ["healthy", "degraded", "unhealthy"]
        if self.default_health_status not in allowed_health_statuses:
            msg = f"default_health_status must be one of {allowed_health_statuses}, got '{self.default_health_status}'"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "allowed_values": ModelSchemaValue.from_value(
                            allowed_health_statuses
                        ),
                        "provided_value": ModelSchemaValue.from_value(
                            self.default_health_status
                        ),
                    },
                ),
            )

        # Validate discovery_channels not empty (only when enabled)
        if self.enabled and not self.discovery_channels:
            msg = "discovery_channels cannot be empty when discovery is enabled"
            raise ModelOnexError(
                message=msg,
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                details=ModelErrorContext.with_context(
                    {
                        "error_type": ModelSchemaValue.from_value("valueerror"),
                        "validation_context": ModelSchemaValue.from_value(
                            "model_validation",
                        ),
                        "provided_value": ModelSchemaValue.from_value(
                            self.discovery_channels
                        ),
                    },
                ),
            )

        # Validate response_throttle_seconds < response_timeout_seconds
        if self.response_throttle_seconds >= self.response_timeout_seconds:
            msg = (
                "response_throttle_seconds must be less than response_timeout_seconds; "
                f"got throttle={self.response_throttle_seconds}s, timeout={self.response_timeout_seconds}s"
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
                        "throttle_seconds": ModelSchemaValue.from_value(
                            self.response_throttle_seconds
                        ),
                        "timeout_seconds": ModelSchemaValue.from_value(
                            self.response_timeout_seconds
                        ),
                    },
                ),
            )

        # Validate max_response_size_bytes reasonable
        if self.max_response_size_bytes > 524288:  # 512 KB
            msg = (
                "max_response_size_bytes exceeding 512KB may cause performance issues; "
                f"got {self.max_response_size_bytes} bytes"
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
                        "recommended_max_bytes": ModelSchemaValue.from_value(524288),
                        "provided_value": ModelSchemaValue.from_value(
                            self.max_response_size_bytes
                        ),
                    },
                ),
            )

        # Validate at least one response content type enabled
        if not any(
            [
                self.include_introspection,
                self.include_event_channels,
                self.include_version_info,
                self.include_health_status,
                self.advertise_capabilities,
            ]
        ):
            msg = (
                "At least one response content type must be enabled "
                "(include_introspection, include_event_channels, include_version_info, "
                "include_health_status, or advertise_capabilities)"
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
                    },
                ),
            )

        return self

    model_config = ConfigDict(
        extra="ignore",  # Allow extra fields from YAML contracts
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_assignment=True,
    )
