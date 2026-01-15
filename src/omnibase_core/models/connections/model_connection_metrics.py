"""
Connection metrics model for network performance tracking.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict


class ModelConnectionMetrics(BaseModel):
    """Connection performance metrics.
    Implements Core protocols:
    - Configurable: Configuration management capabilities
    - Validatable: Validation and verification
    - Serializable: Data serialization/deserialization
    """

    latency_ms: float = Field(
        default=0.0,
        description="Connection latency in milliseconds",
    )
    throughput_mbps: float = Field(
        default=0.0,
        description="Throughput in Mbps",
    )
    packet_loss_percent: float = Field(
        default=0.0,
        description="Packet loss percentage",
    )
    jitter_ms: float = Field(
        default=0.0,
        description="Jitter in milliseconds",
    )
    bytes_sent: int = Field(
        default=0,
        description="Total bytes sent",
    )
    bytes_received: int = Field(
        default=0,
        description="Total bytes received",
    )
    connections_active: int = Field(
        default=0,
        description="Number of active connections",
    )
    connections_total: int = Field(
        default=0,
        description="Total connections opened",
    )
    errors_count: int = Field(
        default=0,
        description="Number of connection errors",
    )
    timeouts_count: int = Field(
        default=0,
        description="Number of connection timeouts",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except ModelOnexError:
            raise  # Re-raise without double-wrapping
        except PYDANTIC_MODEL_ERRORS as e:
            # PYDANTIC_MODEL_ERRORS covers: AttributeError, TypeError, ValidationError, ValueError
            # These are raised by setattr with Pydantic validate_assignment=True
            raise ModelOnexError(
                message=f"Operation failed: {e}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        # Basic validation - Pydantic ensures field types and constraints
        # Override in specific models for custom validation
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)
