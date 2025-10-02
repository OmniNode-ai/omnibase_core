"""
Connection metrics model for network performance tracking.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError


class ModelConnectionMetrics(BaseModel):
    """Connection performance metrics.
    Implements omnibase_spi protocols:
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception as e:
            raise OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)
