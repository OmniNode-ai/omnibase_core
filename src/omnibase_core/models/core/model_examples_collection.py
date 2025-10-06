"""
ModelExamplesCollection - ONEX Standards Compliant.

Examples collection model with comprehensive validation, migration support,
and business intelligence capabilities for ONEX compliance.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports:
- omnibase_core.errors.error_codes (imports only from types.core_types and enums)
- omnibase_core.models.core.model_example (no circular risk)
- omnibase_core.models.core.model_example_metadata (no circular risk)
- pydantic, typing, datetime (standard library)

Import Chain Position:
1. errors.error_codes → types.core_types
2. THIS MODULE → errors.error_codes (OK - no circle)
3. types.constraints → TYPE_CHECKING import of errors.error_codes
4. models.* → types.constraints

This module can safely import error_codes because error_codes only imports
from types.core_types (not from models or types.constraints).
"""

from datetime import UTC, datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode

# Safe runtime import - error_codes only imports from types.core_types
from omnibase_core.errors.model_onex_error import ModelOnexError

from .model_example import ModelExample
from .model_example_metadata import ModelExampleMetadata


class ModelExamplesCollection(BaseModel):
    """
    Enterprise-grade examples collection model with comprehensive validation,
    migration support, and business intelligence capabilities.

    This model manages collections of examples with proper validation,
    metadata tracking, and format conversion capabilities.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    - Migratable: Data migration and compatibility
    """

    # Example entries - properly typed collection of ModelExample
    examples: list[ModelExample] = Field(
        default_factory=list,
        description="List of example data with comprehensive validation",
    )

    # Metadata for examples collection
    metadata: ModelExampleMetadata | None = Field(
        default=None,
        description="Metadata about the examples collection",
    )

    # Collection configuration
    format: str = Field(
        default="json",
        description="Format of examples (json/yaml/text)",
        pattern="^(json|yaml|text)$",
    )

    schema_compliant: bool = Field(
        default=True,
        description="Whether examples comply with schema",
    )

    # Business intelligence fields
    total_examples: int = Field(
        default=0,
        description="Total number of examples (computed)",
        ge=0,
    )

    valid_examples: int = Field(
        default=0,
        description="Number of valid examples (computed)",
        ge=0,
    )

    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # === Validation and Computation Methods ===

    @field_validator("total_examples", mode="before")
    @classmethod
    def compute_total_examples(cls, v: int, info: dict[str, Any]) -> int:
        """Compute total examples from examples list."""
        examples = info.data.get("examples", [])
        return len(examples)

    @field_validator("valid_examples", mode="before")
    @classmethod
    def compute_valid_examples(cls, v: int, info: dict[str, Any]) -> int:
        """Compute valid examples count."""
        examples = info.data.get("examples", [])
        return sum(1 for ex in examples if ex.is_valid)

    @field_validator("last_validated", mode="before")
    @classmethod
    def update_validation_timestamp(
        cls, v: datetime | None, info: dict[str, Any]
    ) -> datetime | None:
        """Update validation timestamp when examples change."""
        examples = info.data.get("examples", [])
        if examples and v is None:
            return datetime.now(UTC)
        return v

    # === Data Conversion Methods ===

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for current standards (Serializable protocol)."""
        # Special compatibility logic for examples
        if len(self.examples) == 1:
            return self.examples[0].model_dump(exclude_none=True)
        return {"examples": [ex.model_dump(exclude_none=True) for ex in self.examples]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Self | None:
        """Create from dictionary for easy migration (Migratable protocol)."""
        if data is None:
            return None

        # Handle different input formats
        if isinstance(data, list):
            examples = [cls._create_example_from_data(item) for item in data]
            return cls(examples=examples)

        if "examples" in data and isinstance(data["examples"], list):
            examples = [
                cls._create_example_from_data(item) for item in data["examples"]
            ]
            return cls(
                examples=examples,
                metadata=data.get("metadata"),
                format=data.get("format", "json"),
                schema_compliant=data.get("schema_compliant", True),
            )

        # Single example as dict
        example = cls._create_example_from_data(data)
        return cls(examples=[example])

    @classmethod
    def _create_example_from_data(cls, data: dict[str, Any] | Any) -> ModelExample:
        """Create ModelExample from various data formats."""
        if isinstance(data, dict):
            # Check if it has required ModelExample fields
            if all(k in data for k in ["input_data", "output_data"]):
                return ModelExample(
                    name=data.get("name"),
                    description=data.get("description"),
                    input_data=data["input_data"],
                    output_data=data["output_data"],
                    context=data.get("context"),
                    tags=data.get("tags", []),
                    is_valid=data.get("is_valid", True),
                    validation_notes=data.get("validation_notes"),
                    created_at=data.get("created_at"),
                    updated_at=data.get("updated_at"),
                )
            else:
                # Treat as input_data
                return ModelExample(
                    input_data=data,
                    name=data.get("name"),
                    description=data.get("description"),
                )
        else:
            # Treat as raw input data
            return ModelExample(
                input_data={"value": data},
                name="Auto-generated example",
                description="Automatically generated from raw data",
            )

    # === Example Management Methods ===

    def add_example(
        self,
        example: ModelExample | dict[str, Any],
        name: str | None = None,
    ) -> None:
        """Add a new example to the collection."""
        if isinstance(example, dict):
            example = self._create_example_from_data(example)

        if name and not example.name:
            example.name = name

        self.examples.append(example)
        # Update computed fields
        self.total_examples = len(self.examples)
        if example.is_valid:
            self.valid_examples += 1
        self.last_validated = datetime.now(UTC)

    def get_example(self, index: int = 0) -> ModelExample | None:
        """Get an example by index."""
        if 0 <= index < len(self.examples):
            return self.examples[index]
        return None

    def remove_example(self, index: int) -> bool:
        """Remove an example by index."""
        if 0 <= index < len(self.examples):
            example = self.examples.pop(index)
            # Update computed fields
            self.total_examples = len(self.examples)
            if example.is_valid:
                self.valid_examples = max(0, self.valid_examples - 1)
            self.last_validated = datetime.now(UTC)
            return True
        return False

    def get_valid_examples(self) -> list[ModelExample]:
        """Get all valid examples."""
        return [ex for ex in self.examples if ex.is_valid]

    def get_invalid_examples(self) -> list[ModelExample]:
        """Get all invalid examples."""
        return [ex for ex in self.examples if not ex.is_valid]

    def validate_all_examples(self) -> None:
        """Validate all examples and update statistics."""
        self.valid_examples = sum(1 for ex in self.examples if ex.is_valid)
        self.last_validated = datetime.now(UTC)

    def is_healthy(self) -> bool:
        """Check if collection is healthy (has valid examples)."""
        return self.total_examples > 0 and self.valid_examples > 0

    def get_validation_rate(self) -> float:
        """Get validation rate as percentage."""
        if self.total_examples == 0:
            return 0.0
        return (self.valid_examples / self.total_examples) * 100.0

    # === Factory Methods ===

    @classmethod
    def create_empty(cls) -> Self:
        """Create an empty examples collection."""
        return cls(
            examples=[],
            metadata=None,
            format="json",
            schema_compliant=True,
        )

    @classmethod
    def create_from_examples(
        cls,
        examples: list[ModelExample | dict[str, Any]],
        metadata: ModelExampleMetadata | None = None,
        format: str = "json",
    ) -> Self:
        """Create collection from list of examples."""
        instance = cls(
            examples=[],
            metadata=metadata,
            format=format,
            schema_compliant=True,
        )

        for example in examples:
            instance.add_example(example)

        return instance

    # === Protocol Method Implementations ===

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure examples are properly structured
            for example in self.examples:
                if not example.validate_instance():
                    return False
            return True
        except Exception:
            # fallback-ok: validation failure defaults to invalid state
            return False
