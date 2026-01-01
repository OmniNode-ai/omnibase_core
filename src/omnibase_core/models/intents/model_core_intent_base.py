"""
Base class for core infrastructure intents.

This module provides the ModelCoreIntent base class that all core infrastructure
intents inherit from. Core intents use a discriminated union pattern for
type-safe, exhaustive handling.

Design Pattern:
    Core intents represent a CLOSED SET of known side effects that Reducers can
    emit. Each intent type has its own schema with a `kind` discriminator field,
    enabling structural pattern matching in Effect nodes.

    The discriminated union pattern provides:
    - Compile-time type safety via Annotated[Union[...], Field(discriminator="kind")]
    - Exhaustive handling enforcement (add new intent -> update all handlers)
    - Clear separation of concerns (Reducer declares intent, Effect executes)

Architecture:
    Reducer function: delta(state, action) -> (new_state, intents[])

    1. Reducer emits typed intents (does NOT perform side effects)
    2. Effect receives intents via discriminated union type
    3. Effect pattern-matches on intent type and executes side effect
    4. correlation_id links intent to originating request for tracing

Thread Safety:
    ModelCoreIntent is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access. Note that this provides shallow
    immutability - nested mutable objects should be avoided.

Example:
    >>> from omnibase_core.models.intents import ModelCoreIntent
    >>> from uuid import uuid4
    >>>
    >>> # Base class is abstract - use concrete subclasses
    >>> class MyCustomIntent(ModelCoreIntent):
    ...     kind: Literal["my.custom"] = "my.custom"
    ...     payload: str

See Also:
    omnibase_core.models.intents.ModelCoreRegistrationIntent: Discriminated union type
    omnibase_core.models.intents.ModelConsulRegisterIntent: Consul registration
    omnibase_core.models.intents.ModelConsulDeregisterIntent: Consul deregistration
    omnibase_core.models.intents.ModelPostgresUpsertRegistrationIntent: PostgreSQL upsert
    omnibase_core.models.reducer.model_intent.ModelIntent: Extension intents (plugins)
"""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelCoreIntent(BaseModel):
    """Base class for all core infrastructure intents.

    All core intents share a correlation_id for distributed tracing.
    Subclasses define the specific intent schema and a `kind` discriminator
    field for the discriminated union pattern.

    Core intents are a CLOSED SET. Each intent has its own schema.
    Dispatch is structural (pattern matching on type), not string-based.

    Subclassing Requirements:
        1. Define `kind: Literal["your.kind"] = "your.kind"` as discriminator
        2. Add intent to ModelCoreRegistrationIntent union in __init__.py
        3. Update all Effect dispatch handlers for exhaustive matching

    Attributes:
        correlation_id: UUID for distributed tracing across services. Links
            the intent to the originating request throughout the system.

    Example:
        >>> from uuid import uuid4
        >>> from typing import Literal
        >>>
        >>> class ModelMyIntent(ModelCoreIntent):
        ...     kind: Literal["my.intent"] = "my.intent"
        ...     data: str
        >>>
        >>> intent = ModelMyIntent(
        ...     correlation_id=uuid4(),
        ...     data="example",
        ... )
    """

    correlation_id: UUID = Field(
        ...,
        description=(
            "Correlation ID for distributed tracing. Links this intent to the "
            "originating request across service boundaries."
        ),
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
        from_attributes=True,
    )

    # ONEX_EXCLUDE: dict_str_any - model_dump serialization output
    def serialize_for_io(self) -> dict[str, Any]:
        """Serialize intent for I/O operations.

        Called by Effects at the serialization boundary.
        Reducers MUST NOT call this method.

        Uses `serialize_as_any=True` to properly serialize polymorphic BaseModel
        fields. This ensures that when an intent contains a field typed as
        `BaseModel` (e.g., `record: BaseModel` in ModelPostgresUpsertRegistrationIntent),
        subclass fields are included in the serialized output rather than being
        truncated to only the base class fields.

        Returns:
            JSON-serializable dictionary representation with full polymorphic
            subclass serialization.
        """
        return self.model_dump(mode="json", serialize_as_any=True)
