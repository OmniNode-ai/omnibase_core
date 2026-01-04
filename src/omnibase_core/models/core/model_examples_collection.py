"""
ModelExamplesCollection.

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
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Safe runtime import - error_codes only imports from types.core_types
from omnibase_core.models.examples.model_example import ModelExample
from omnibase_core.models.examples.model_example_metadata import ModelExampleMetadata
from omnibase_core.types.type_json import JsonType
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelExamplesCollection(BaseModel):
    """
    Enterprise-grade examples collection model with comprehensive validation,
    migration support, and business intelligence capabilities.

    This model manages collections of examples with proper validation,
    metadata tracking, and format conversion capabilities.
    Implements Core protocols:
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

    # Timestamp field (mutable, auto-populated on creation if examples exist)
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # === Computed Fields (Business Intelligence) ===

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_examples(self) -> int:
        """Total number of examples (computed from examples list).

        This is a computed field that always reflects the current examples count.
        Type safety is guaranteed since examples are validated as ModelExample instances.
        """
        return len(self.examples)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid_examples(self) -> int:
        """Number of valid examples (computed from examples list).

        This is a computed field that counts examples where is_valid=True.
        Type safety is guaranteed since examples are validated as ModelExample instances.
        """
        return sum(1 for ex in self.examples if ex.is_valid)

    # === Validation Methods ===

    @model_validator(mode="after")
    def auto_populate_timestamp(self) -> Self:
        """Auto-populate validation timestamp when creating new collections with examples.

        This validator implements "auto-timestamp on creation" behavior:
        - If examples exist AND no timestamp was provided, sets it to now
        - If a timestamp was explicitly provided, preserves that value
        - If no examples exist, leaves the timestamp as None

        Uses object.__setattr__ to bypass validate_assignment and avoid recursion.
        """
        if self.examples and self.last_validated is None:
            # Use object.__setattr__ to bypass validate_assignment recursion
            object.__setattr__(self, "last_validated", datetime.now(UTC))
        return self

    # === Data Conversion Methods ===

    def to_dict(self) -> SerializedDict:
        """Convert to dictionary for current standards (Serializable protocol)."""
        # Special compatibility logic for examples
        if len(self.examples) == 1:
            return self.examples[0].model_dump(exclude_none=True)
        return {"examples": [ex.model_dump(exclude_none=True) for ex in self.examples]}

    @classmethod
    def from_dict(cls, data: SerializedDict | None) -> Self | None:
        """Create from dictionary for easy migration (Migratable protocol)."""
        if data is None:
            return None

        # Handle different input formats - data is guaranteed to be dict by type annotation
        if "examples" in data and isinstance(data["examples"], list):
            examples = [
                cls._create_example_from_data(item) for item in data["examples"]
            ]
            # Extract metadata - can be None, dict, or ModelExampleMetadata
            metadata_raw = data.get("metadata")
            metadata: ModelExampleMetadata | None = None
            if metadata_raw is not None:
                if isinstance(metadata_raw, ModelExampleMetadata):
                    metadata = metadata_raw
                elif isinstance(metadata_raw, dict):
                    metadata = ModelExampleMetadata.model_validate(metadata_raw)

            # Extract format with type-safe default
            format_val = data.get("format")
            format_str = str(format_val) if isinstance(format_val, str) else "json"

            # Extract schema_compliant with type-safe default
            schema_val = data.get("schema_compliant")
            schema_compliant = schema_val if isinstance(schema_val, bool) else True

            return cls(
                examples=examples,
                metadata=metadata,
                format=format_str,
                schema_compliant=schema_compliant,
            )

        # Single example as dict
        example = cls._create_example_from_data(data)
        return cls(examples=[example])

    @classmethod
    def _create_example_from_data(cls, data: JsonType) -> ModelExample:
        """Create ModelExample from various data formats."""
        from omnibase_core.models.examples.model_example_context_data import (
            ModelExampleContextData,
        )
        from omnibase_core.models.examples.model_example_data import (
            ModelExampleInputData,
            ModelExampleOutputData,
        )

        if isinstance(data, dict):
            # Check if it has required ModelExample fields
            if all(k in data for k in ["input_data", "output_data"]):
                # Convert dicts to proper types using model_validate for type-safe coercion
                input_data: ModelExampleInputData | None = None
                input_raw = data.get("input_data")
                if input_raw is not None:
                    if isinstance(input_raw, dict):
                        try:
                            input_data = ModelExampleInputData.model_validate(input_raw)
                        except PYDANTIC_MODEL_ERRORS as e:
                            # boundary-ok: convert pydantic validation errors to ModelOnexError
                            raise ModelOnexError(
                                message=f"Failed to validate input_data: {e}",
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                                context={"input_data": input_raw},
                            ) from e
                    elif isinstance(input_raw, ModelExampleInputData):
                        input_data = input_raw
                    # Other types are skipped (leave as None)

                output_data: ModelExampleOutputData | None = None
                output_raw = data.get("output_data")
                if output_raw is not None:
                    if isinstance(output_raw, dict):
                        try:
                            output_data = ModelExampleOutputData.model_validate(
                                output_raw
                            )
                        except PYDANTIC_MODEL_ERRORS as e:
                            # boundary-ok: convert pydantic validation errors to ModelOnexError
                            raise ModelOnexError(
                                message=f"Failed to validate output_data: {e}",
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                                context={"output_data": output_raw},
                            ) from e
                    elif isinstance(output_raw, ModelExampleOutputData):
                        output_data = output_raw
                    # Other types are skipped (leave as None)

                context: ModelExampleContextData | None = None
                context_raw = data.get("context")
                if context_raw is not None:
                    if isinstance(context_raw, dict):
                        try:
                            context = ModelExampleContextData.model_validate(
                                context_raw
                            )
                        except PYDANTIC_MODEL_ERRORS as e:
                            # boundary-ok: convert pydantic validation errors to ModelOnexError
                            raise ModelOnexError(
                                message=f"Failed to validate context: {e}",
                                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                                context={"context_data": context_raw},
                            ) from e
                    elif isinstance(context_raw, ModelExampleContextData):
                        context = context_raw
                    # Other types are skipped (leave as None)

                # Get values with type-safe defaults
                name_val = data.get("name")
                name = str(name_val) if name_val is not None else "Example"
                desc_val = data.get("description")
                description = str(desc_val) if desc_val is not None else ""
                tags_val = data.get("tags")
                # Properly coerce tags to list[str] - convert all elements to strings
                if isinstance(tags_val, list):
                    tags: list[str] = [str(t) for t in tags_val]
                else:
                    tags = []
                is_valid_val = data.get("is_valid")
                # Only accept actual bool values to avoid surprising coercion
                # (e.g., bool("false") == True which is unexpected)
                if isinstance(is_valid_val, bool):
                    is_valid = is_valid_val
                else:
                    is_valid = True  # Default to valid if not explicitly a bool
                notes_val = data.get("validation_notes")
                validation_notes = str(notes_val) if notes_val is not None else ""

                return ModelExample(
                    name=name,
                    description=description,
                    input_data=input_data,
                    output_data=output_data,
                    context=context,
                    tags=tags,
                    is_valid=is_valid,
                    validation_notes=validation_notes,
                )
            else:
                # Treat as input_data - use model_validate for type-safe coercion
                try:
                    input_data = ModelExampleInputData.model_validate(data)
                except PYDANTIC_MODEL_ERRORS as e:
                    # boundary-ok: convert pydantic validation errors to ModelOnexError
                    raise ModelOnexError(
                        message=f"Failed to validate example data as input_data: {e}",
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        context={"data": data},
                    ) from e
                name_val = data.get("name")
                name = str(name_val) if name_val is not None else "Example"
                desc_val = data.get("description")
                description = str(desc_val) if desc_val is not None else ""
                return ModelExample(
                    name=name,
                    description=description,
                    input_data=input_data,
                )
        else:
            # Treat as raw input data
            return ModelExample(
                input_data=ModelExampleInputData(),
                name="Auto-generated example",
                description="Automatically generated from raw data",
            )

    # === Example Management Methods ===

    def add_example(
        self,
        example: ModelExample | SerializedDict,
        name: str | None = None,
    ) -> None:
        """Add a new example to the collection.

        Note: total_examples and valid_examples are computed properties that
        automatically reflect the current state of the examples list.
        """
        if isinstance(example, dict):
            example = self._create_example_from_data(example)

        if name and not example.name:
            example.name = name

        self.examples.append(example)
        # Update timestamp (computed fields are auto-updated)
        # Use object.__setattr__ to bypass validate_assignment for timestamp-only updates
        object.__setattr__(self, "last_validated", datetime.now(UTC))

    def get_example(self, index: int = 0) -> ModelExample | None:
        """Get an example by index."""
        if 0 <= index < len(self.examples):
            return self.examples[index]
        return None

    def remove_example(self, index: int) -> bool:
        """Remove an example by index.

        Note: total_examples and valid_examples are computed properties that
        automatically reflect the current state of the examples list.
        """
        if 0 <= index < len(self.examples):
            self.examples.pop(index)
            # Update timestamp (computed fields are auto-updated)
            # Use object.__setattr__ to bypass validate_assignment for timestamp-only updates
            object.__setattr__(self, "last_validated", datetime.now(UTC))
            return True
        return False

    def get_valid_examples(self) -> list[ModelExample]:
        """Get all valid examples."""
        return [ex for ex in self.examples if ex.is_valid]

    def get_invalid_examples(self) -> list[ModelExample]:
        """Get all invalid examples."""
        return [ex for ex in self.examples if not ex.is_valid]

    def validate_all_examples(self) -> None:
        """Validate all examples and update timestamp.

        Note: valid_examples is a computed property that automatically
        reflects the current validation state. This method updates the
        last_validated timestamp to indicate when validation was last run.
        """
        # Use object.__setattr__ to bypass validate_assignment for timestamp-only updates
        object.__setattr__(self, "last_validated", datetime.now(UTC))

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
        examples: list[ModelExample | SerializedDict],
        metadata: ModelExampleMetadata | None = None,
        example_format: str = "json",
    ) -> Self:
        """Create collection from list of examples."""
        instance = cls(
            examples=[],
            metadata=metadata,
            format=example_format,
            schema_compliant=True,
        )

        for example in examples:
            instance.add_example(example)

        return instance

    # === Protocol Method Implementations ===

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure examples are properly structured
            for example in self.examples:
                # Validate that example is a proper ModelExample instance
                # and has required fields
                if not isinstance(example, ModelExample) or not hasattr(
                    example, "input_data"
                ):
                    return False
            return True
        except (AttributeError, TypeError, ValueError):
            # fallback-ok: validation failure defaults to invalid state
            # AttributeError: if example lacks expected attributes
            # TypeError: if self.examples is not iterable
            # ValueError: if comparison operations fail
            return False
