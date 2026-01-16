"""Output field model for event bus processing results.

Thread Safety:
    ModelEventBusOutputField instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelEventBusOutputField(BaseModel):
    """
    Output field for event bus processing results.

    Contains the processing outcome including transformed data, integration flags,
    backend identifier, and optional custom metadata.

    Attributes:
        processed: The processed/transformed output string, if any.
        integration: Flag indicating whether integration mode was used.
        backend: Identifier for the backend that processed this field.
        custom: Optional custom metadata. Type is intentionally object for flexibility
            in storing arbitrary user-defined data structures. Consumers should
            validate the structure before use.
    """

    # Note on frozen=True: This output field is immutable to prevent accidental
    # mutation after creation.
    # Note on from_attributes=True: Added for pytest-xdist parallel execution
    # compatibility. See CLAUDE.md "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    processed: str | None = Field(
        default=None,
        description="The processed/transformed output string",
    )
    integration: bool | None = Field(
        default=None,
        description="Flag indicating whether integration mode was used",
    )
    backend: str = Field(
        ...,
        description="Identifier for the backend that processed this field",
    )
    # Note: custom is intentionally typed as object for flexibility in storing
    # arbitrary user-defined data structures. Consumers should validate the
    # structure before use. This is a common pattern for extensible metadata.
    custom: object | None = Field(
        default=None,
        description="Optional custom metadata (arbitrary structure)",
    )

    def has_processed_output(self) -> bool:
        """Check if there is a processed output value."""
        return self.processed is not None and len(self.processed) > 0

    def has_custom_data(self) -> bool:
        """Check if custom metadata is present."""
        return self.custom is not None

    @classmethod
    def create_simple(
        cls, backend: str, processed: str | None = None
    ) -> "ModelEventBusOutputField":
        """Create a simple output field with just backend and optional processed value."""
        return cls(backend=backend, processed=processed)

    @classmethod
    def create_with_custom(
        cls, backend: str, custom: object, processed: str | None = None
    ) -> "ModelEventBusOutputField":
        """Create an output field with custom metadata."""
        return cls(backend=backend, processed=processed, custom=custom)


__all__ = ["ModelEventBusOutputField"]
