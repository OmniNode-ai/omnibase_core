"""
Execution Mode Model

Replaces EnumExecutionMode with a proper model that includes all properties
as fields instead of methods.
"""

from pydantic import BaseModel, Field


class ModelExecutionMode(BaseModel):
    """
    Execution mode with all properties as fields.

    Replaces the EnumExecutionMode enum to provide structured data
    instead of methods while maintaining compatibility.
    """

    # Core fields (required)
    name: str = Field(
        default=...,
        description="Execution mode identifier (DIRECT, INMEMORY, EVENT_BUS)",
        pattern="^[A-Z]+$",
    )

    value: str = Field(
        default=...,
        description="Lowercase value for current standards (direct, inmemory, event_bus)",
    )

    # Properties as fields (replacing methods)
    is_synchronous: bool = Field(
        default=...,
        description="Whether this execution mode is synchronous",
    )

    is_asynchronous: bool = Field(
        default=...,
        description="Whether this execution mode is asynchronous",
    )

    is_distributed: bool = Field(
        default=...,
        description="Whether this execution mode is distributed",
    )

    is_local: bool = Field(
        default=..., description="Whether this execution mode is local"
    )

    requires_event_bus: bool = Field(
        default=...,
        description="Whether this mode requires an event bus",
    )

    supports_scaling: bool = Field(
        default=...,
        description="Whether this mode supports horizontal scaling",
    )

    typical_latency_ms: int = Field(
        default=...,
        description="Typical latency for this execution mode in milliseconds",
        gt=0,
    )

    reliability_level: str = Field(
        default=...,
        description="Reliability level (low, medium, high)",
        pattern="^(low|medium|high)$",
    )

    # Optional metadata
    description: str = Field(
        default="",
        description="Human-readable description of the execution mode",
    )

    supported_node_types: list[str] = Field(
        default_factory=lambda: ["full"],
        description="Node types that support this execution mode",
    )

    # Factory methods for standard execution modes
    @classmethod
    def DIRECT(cls) -> "ModelExecutionMode":
        """Direct execution mode - synchronous, local execution."""
        return cls(
            name="DIRECT",
            value="direct",
            is_synchronous=True,
            is_asynchronous=False,
            is_distributed=False,
            is_local=True,
            requires_event_bus=False,
            supports_scaling=False,
            typical_latency_ms=5,
            reliability_level="low",
            description="Direct synchronous execution with minimal overhead",
            supported_node_types=["full", "reducer", "processor"],
        )

    @classmethod
    def INMEMORY(cls) -> "ModelExecutionMode":
        """In-memory execution mode - asynchronous, local event bus."""
        return cls(
            name="INMEMORY",
            value="inmemory",
            is_synchronous=False,
            is_asynchronous=True,
            is_distributed=False,
            is_local=True,
            requires_event_bus=True,
            supports_scaling=False,
            typical_latency_ms=20,
            reliability_level="medium",
            description="Asynchronous execution with in-memory event bus",
            supported_node_types=["full", "reducer", "processor", "async"],
        )

    @classmethod
    def EVENT_BUS(cls) -> "ModelExecutionMode":
        """Event bus execution mode - asynchronous, distributed event bus."""
        return cls(
            name="EVENT_BUS",
            value="event_bus",
            is_synchronous=False,
            is_asynchronous=True,
            is_distributed=True,
            is_local=False,
            requires_event_bus=True,
            supports_scaling=True,
            typical_latency_ms=100,
            reliability_level="high",
            description="Distributed asynchronous execution with event bus",
            supported_node_types=[
                "full",
                "reducer",
                "processor",
                "async",
                "distributed",
            ],
        )

    @classmethod
    def from_string(cls, mode: str) -> "ModelExecutionMode":
        """Create ModelExecutionMode from string for current standards."""
        mode_upper = mode.upper()
        if mode_upper == "DIRECT":
            return cls.DIRECT()
        if mode_upper == "INMEMORY":
            return cls.INMEMORY()
        if mode_upper == "EVENT_BUS":
            return cls.EVENT_BUS()
        # Unknown mode - create a generic one
        return cls(
            name=mode_upper,
            value=mode.lower(),
            is_synchronous=False,
            is_asynchronous=True,
            is_distributed=False,
            is_local=True,
            requires_event_bus=False,
            supports_scaling=False,
            typical_latency_ms=50,
            reliability_level="medium",
            description=f"Custom execution mode: {mode}",
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            return self.value == other or self.name == other.upper()
        if isinstance(other, ModelExecutionMode):
            return self.name == other.name
        return False

    # Compatibility methods (same signatures as enum)
    def get_typical_latency_ms(self) -> int:
        """Get typical latency for this execution mode."""
        return self.typical_latency_ms

    def get_reliability_level(self) -> str:
        """Get reliability level for this execution mode."""
        return self.reliability_level
