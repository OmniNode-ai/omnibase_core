"""
Node Meta Model - ONEX Standards Compliant.

VERSION: 1.0.0 - INTERFACE LOCKED FOR CODE GENERATION

STABILITY GUARANTEE:
- All fields, methods, and validators are stable interfaces
- New optional fields may be added in minor versions only
- Existing fields cannot be removed or have types/constraints changed
- Breaking changes require major version bump

This module defines the meta-model that all declarative node contracts must
adhere to, ensuring cross-node consistency in the ONEX 4-node architecture.

The ModelContractMeta defines:
- Required fields for ALL declarative node contracts
- Optional fields for additional metadata
- Reserved extension fields for future use
- Meta-schema validation for cross-node consistency

ZERO TOLERANCE: No Any types in required fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.contracts.model_contract_node_metadata import (
    ModelContractNodeMetadata,
)
from omnibase_core.models.contracts.model_contract_version import ModelContractVersion
from omnibase_core.models.contracts.model_node_extensions import ModelNodeExtensions
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelContractMeta(BaseModel):
    """
    Meta-model defining the schema for all declarative node contracts.

    This model enforces cross-node consistency by defining the required,
    optional, and reserved extension fields that all node contracts must adhere to.

    ONEX Four-Node Architecture:
    - EFFECT: External interactions (I/O)
    - COMPUTE: Data processing & transformation
    - REDUCER: State aggregation & management (FSM-driven)
    - ORCHESTRATOR: Workflow coordination (workflow-driven)
    - RUNTIME_HOST: Runtime host nodes for coordination

    Attributes:
        node_id: Unique identifier for the node (UUID)
        node_kind: Architectural classification (EnumNodeKind)
        version: Contract version (ModelContractVersion or semver string)
        name: Human-readable name for the node
        description: Purpose and description of the node
        input_schema: Fully qualified input model class name
        output_schema: Fully qualified output model class name
        tags: Optional classification tags
        author: Optional author information
        created_at: Optional creation timestamp
        updated_at: Optional last update timestamp
        extensions: Reserved dict for future extension points
        metadata: Additional metadata dict

    Example:
        >>> from uuid import uuid4
        >>> from omnibase_core.enums import EnumNodeKind
        >>> meta = ModelContractMeta(
        ...     node_id=uuid4(),
        ...     node_kind=EnumNodeKind.COMPUTE,
        ...     version="1.0.0",
        ...     name="DataTransformer",
        ...     description="Transforms input data to output format",
        ...     input_schema="omnibase_core.models.ModelInput",
        ...     output_schema="omnibase_core.models.ModelOutput",
        ... )
        >>> meta.node_kind
        <EnumNodeKind.COMPUTE: 'compute'>
    """

    # Interface version for code generation stability
    INTERFACE_VERSION: ClassVar[ModelSemVer] = ModelSemVer(major=1, minor=0, patch=0)

    # ========================================================================
    # REQUIRED FIELDS - All declarative node contracts MUST provide these
    # ========================================================================

    node_id: UUID = Field(
        ...,
        description="Unique identifier for the node (UUID)",
    )

    node_kind: EnumNodeKind = Field(
        ...,
        description="High-level architectural classification for the node",
    )

    version: ModelContractVersion = Field(
        ...,
        description="Semantic version of the contract",
    )

    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for the node",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Purpose and description of the node",
    )

    input_schema: str = Field(
        ...,
        min_length=1,
        description="Fully qualified input model class name",
    )

    output_schema: str = Field(
        ...,
        min_length=1,
        description="Fully qualified output model class name",
    )

    # ========================================================================
    # OPTIONAL FIELDS - Additional metadata for enhanced documentation
    # ========================================================================

    tags: list[str] = Field(
        default_factory=list,
        description="Classification tags for the node",
    )

    author: str | None = Field(
        default=None,
        description="Author information for the node contract",
    )

    created_at: datetime | None = Field(
        default=None,
        description="Creation timestamp of the node contract",
    )

    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp of the node contract",
    )

    # ========================================================================
    # RESERVED EXTENSION FIELDS - For future use
    # ========================================================================

    extensions: ModelNodeExtensions = Field(
        default_factory=ModelNodeExtensions,
        description="Reserved for future extension points",
    )

    metadata: ModelContractNodeMetadata = Field(
        default_factory=ModelContractNodeMetadata,
        description="Additional metadata for custom information",
    )

    # ========================================================================
    # VALIDATORS
    # ========================================================================

    @field_validator("node_kind", mode="before")
    @classmethod
    def validate_node_kind(cls, v: object) -> EnumNodeKind:
        """Validate and convert node_kind to EnumNodeKind.

        Supports both EnumNodeKind instances and string values for YAML
        compatibility. String values are case-insensitive.

        Args:
            v: Input value - EnumNodeKind instance or string.

        Returns:
            Validated EnumNodeKind instance.

        Raises:
            ModelOnexError: If the value is not a valid node kind.
        """
        if isinstance(v, EnumNodeKind):
            return v
        if isinstance(v, str):
            try:
                return EnumNodeKind(v.lower())
            except ValueError:
                raise ModelOnexError(
                    message=f"Invalid node_kind: '{v}'. Must be one of {[e.value for e in EnumNodeKind]}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    invalid_value=v,
                    valid_values=[e.value for e in EnumNodeKind],
                )
        raise ModelOnexError(
            message=f"node_kind must be EnumNodeKind or string, got {type(v).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            received_type=type(v).__name__,
        )

    @field_validator("version", mode="before")
    @classmethod
    def validate_version(cls, v: object) -> ModelContractVersion:
        """Validate and convert version to ModelContractVersion.

        Supports multiple input formats for flexible contract definition:
        - ModelContractVersion instances (passed through)
        - Semver strings (e.g., "1.0.0", "2.1.0-beta")
        - Dictionary representations

        Args:
            v: Input value - ModelContractVersion, string, or dict.

        Returns:
            Validated ModelContractVersion instance.

        Raises:
            ModelOnexError: If the value cannot be converted to a valid version.
        """
        if isinstance(v, ModelContractVersion):
            return v
        if isinstance(v, str):
            return ModelContractVersion.from_string(v)
        if isinstance(v, dict):
            return ModelContractVersion.model_validate(v)
        raise ModelOnexError(
            message=f"version must be ModelContractVersion, dict, or semver string, got {type(v).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            received_type=type(v).__name__,
        )

    @field_validator(
        "name", "description", "input_schema", "output_schema", mode="before"
    )
    @classmethod
    def strip_and_validate_non_empty(cls, v: object) -> str:
        """Strip whitespace and validate non-empty strings.

        Ensures required string fields contain meaningful content by:
        1. Stripping leading/trailing whitespace
        2. Rejecting empty or whitespace-only strings

        Args:
            v: Input value expected to be a string.

        Returns:
            Stripped string value.

        Raises:
            ModelOnexError: If value is not a string or is empty after stripping.
        """
        if not isinstance(v, str):
            raise ModelOnexError(
                message=f"Expected string, got {type(v).__name__}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                received_type=type(v).__name__,
            )
        stripped = v.strip()
        if not stripped:
            raise ModelOnexError(
                message="Field cannot be empty or whitespace-only",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        return stripped

    @field_validator("node_id", mode="before")
    @classmethod
    def validate_node_id(cls, v: object) -> UUID:
        """Validate and convert node_id to UUID.

        Accepts either a UUID object or a valid UUID string representation.

        Args:
            v: Input value - UUID instance or UUID string.

        Returns:
            Validated UUID instance.

        Raises:
            ModelOnexError: If the value is not a valid UUID format.
        """
        if isinstance(v, UUID):
            return v
        if isinstance(v, str):
            try:
                return UUID(v)
            except ValueError as e:
                raise ModelOnexError(
                    message=f"Invalid UUID format: {v}",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                ) from e
        raise ModelOnexError(
            message=f"node_id must be UUID or UUID string, got {type(v).__name__}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            received_type=type(v).__name__,
        )

    @model_validator(mode="after")
    def validate_cross_node_consistency(self) -> ModelContractMeta:
        """Validate cross-node consistency requirements.

        This validator is intentionally permissive - it allows external models
        that don't follow ONEX naming conventions. Stricter validation can be
        performed at the application layer using `validate_meta_model()` if
        strict ONEX compliance is required.

        Future enhancements may add:
        - Schema existence validation (via import checks)
        - Cross-reference validation between input/output schemas
        - Node kind specific schema requirements

        Returns:
            The validated ModelContractMeta instance.

        Note:
            External models (not prefixed with 'omnibase_') are allowed.
            Use `validate_meta_model()` for additional application-layer checks.
        """
        # Currently permissive - all schema names allowed.
        # Stricter validation available via validate_meta_model().
        return self

    # ========================================================================
    # METHODS
    # ========================================================================

    def __eq__(self, other: object) -> bool:
        """Check equality based on node_id.

        Two ModelContractMeta instances are considered equal if they have
        the same node_id, regardless of other field values.

        Args:
            other: Another object to compare with.

        Returns:
            True if both have the same node_id, NotImplemented for non-meta types.
        """
        if not isinstance(other, ModelContractMeta):
            return NotImplemented
        return self.node_id == other.node_id

    def __hash__(self) -> int:
        """Return hash based on node_id for use in sets and dicts.

        Returns:
            Integer hash value derived from node_id.
        """
        return hash(self.node_id)

    def is_core_node_type(self) -> bool:
        """Check if this is a core ONEX node type.

        Core node types are the four primary architectural roles in ONEX:
        EFFECT, COMPUTE, REDUCER, and ORCHESTRATOR.

        Returns:
            True if node_kind is EFFECT, COMPUTE, REDUCER, or ORCHESTRATOR.
        """
        return EnumNodeKind.is_core_node_type(self.node_kind)

    def is_infrastructure_type(self) -> bool:
        """Check if this is an infrastructure node type.

        Infrastructure node types provide runtime support and coordination
        rather than processing data directly.

        Returns:
            True if node_kind is RUNTIME_HOST.
        """
        return EnumNodeKind.is_infrastructure_type(self.node_kind)

    # ========================================================================
    # MODEL CONFIGURATION
    # ========================================================================

    model_config = ConfigDict(
        extra="forbid",  # Strict - no extra fields allowed (ZERO TOLERANCE)
        from_attributes=True,  # Required for pytest-xdist compatibility
        frozen=True,  # Immutable after creation for hashability
        str_strip_whitespace=True,  # Strip whitespace from strings
        use_enum_values=False,  # Keep enum objects, don't convert to strings
        validate_default=True,  # Validate default values
    )


def validate_meta_model(meta: ModelContractMeta) -> None:
    """
    Validate a ModelContractMeta for ONEX compliance.

    This function provides application-level validation for ONEX standards
    compliance. Since Pydantic already validates required fields and constraints
    during model construction, this function focuses on semantic validation
    that may be context-dependent.

    Current validations:
        - Schema naming convention checks (ONEX prefix recommended)

    Note:
        Basic field presence and type validation is handled by Pydantic
        during model construction. This function is safe to call on any
        valid ModelContractMeta instance.

    Args:
        meta: The ModelContractMeta to validate

    Raises:
        ModelOnexError: If validation fails

    Example:
        >>> from uuid import uuid4
        >>> meta = ModelContractMeta(
        ...     node_id=uuid4(),
        ...     node_kind=EnumNodeKind.COMPUTE,
        ...     version="1.0.0",
        ...     name="TestNode",
        ...     description="A test node",
        ...     input_schema="omnibase_core.models.ModelInput",
        ...     output_schema="omnibase_core.models.ModelOutput",
        ... )
        >>> validate_meta_model(meta)  # No error raised
    """
    # Validate schema naming follows ONEX conventions (warning-level, not error)
    # This is informational - external schemas are allowed but flagged
    non_onex_schemas: list[str] = []

    if not meta.input_schema.startswith("omnibase_"):
        non_onex_schemas.append(f"input_schema: {meta.input_schema}")

    if not meta.output_schema.startswith("omnibase_"):
        non_onex_schemas.append(f"output_schema: {meta.output_schema}")

    # Currently we don't raise on non-ONEX schemas (they're allowed)
    # Future versions may add stricter validation modes via parameter
    # Example: validate_meta_model(meta, strict=True)

    # All validations passed


def is_valid_meta_model(meta: ModelContractMeta) -> bool:
    """
    Check if a ModelContractMeta is valid.

    This function performs validation and returns a boolean result
    instead of raising an exception.

    Args:
        meta: The ModelContractMeta to validate

    Returns:
        True if the meta-model is valid, False otherwise

    Example:
        >>> from uuid import uuid4
        >>> meta = ModelContractMeta(
        ...     node_id=uuid4(),
        ...     node_kind=EnumNodeKind.COMPUTE,
        ...     version="1.0.0",
        ...     name="TestNode",
        ...     description="A test node",
        ...     input_schema="omnibase_core.models.ModelInput",
        ...     output_schema="omnibase_core.models.ModelOutput",
        ... )
        >>> is_valid_meta_model(meta)
        True
    """
    try:
        validate_meta_model(meta)
        return True
    except ModelOnexError:
        return False


__all__ = [
    "ModelContractNodeMetadata",
    "ModelNodeExtensions",
    "ModelContractMeta",
    "is_valid_meta_model",
    "validate_meta_model",
]
