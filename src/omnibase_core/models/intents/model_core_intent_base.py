"""
Base class for core infrastructure intents.

This module provides the ModelCoreIntent base class that all core infrastructure
intents inherit from. Core intents use a discriminated union pattern for
type-safe, exhaustive handling.

Thread Safety:
    ModelCoreIntent is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access.

See Also:
    - model_consul_register_intent: Consul registration intent
    - model_consul_deregister_intent: Consul deregistration intent
    - model_postgres_upsert_registration_intent: PostgreSQL upsert intent
    - omnibase_core.models.reducer.model_intent: Extension intents (plugins)
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.utils.util_decorators import allow_dict_str_any


@allow_dict_str_any(
    "serialize_for_io() returns dict[str, Any] for JSON serialization at I/O boundary. "
    "This is the serialization point where typed data becomes untyped for transport."
)
class ModelCoreIntent(BaseModel):
    """Base class for all core infrastructure intents.

    All core intents share a correlation_id for distributed tracing.
    Subclasses define the specific intent schema and discriminator.

    Core intents are a CLOSED SET. Each intent has its own schema.
    Dispatch is structural (pattern matching on type), not string-based.

    Attributes:
        correlation_id: UUID for distributed tracing across services.
    """

    correlation_id: UUID = Field(
        ...,
        description="Correlation ID for distributed tracing",
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    def serialize_for_io(self) -> dict[str, Any]:
        """Serialize intent for I/O operations.

        Called by Effects at the serialization boundary.
        Reducers MUST NOT call this method.

        Returns:
            JSON-serializable dictionary representation.
        """
        return self.model_dump(mode="json")
