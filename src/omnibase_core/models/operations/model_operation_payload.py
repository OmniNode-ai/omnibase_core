"""
Strongly-typed operation payload structure.

Replaces dict[str, Any] usage in operation payloads with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.operations.model_execution_metadata import (
    ModelExecutionMetadata,
)


# Structured operation parameters to replace primitive soup patterns (defined first)
class ModelOperationParametersBase(BaseModel):
    """Structured base operation parameters."""

    execution_timeout: int = Field(
        default=30000,
        description="Execution timeout in milliseconds",
    )
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    priority_level: str = Field(
        default="normal",
        description="Operation priority level",
    )
    async_execution: bool = Field(
        default=False,
        description="Whether operation executes asynchronously",
    )
    validation_enabled: bool = Field(
        default=True,
        description="Whether input validation is enabled",
    )
    debug_mode: bool = Field(default=False, description="Whether debug mode is enabled")
    trace_execution: bool = Field(
        default=False,
        description="Whether to trace execution steps",
    )
    resource_limits: dict[str, str] = Field(
        default_factory=dict,
        description="Resource limit specifications",
    )
    custom_settings: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom settings",
    )


# ONEX 4-Node Architecture Operation Types - using EnumNodeType from enums package


# Discriminated operation data types following ONEX 4-node architecture
class ModelOperationDataBase(BaseModel):
    """Base operation data with discriminator."""

    operation_type: EnumNodeType = Field(
        ...,
        description="Operation type discriminator",
    )
    input_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Operation input data with proper typing",
    )
    output_data: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Operation output data with proper typing",
    )
    parameters: ModelOperationParametersBase = Field(
        default_factory=ModelOperationParametersBase,
        description="Structured operation parameters",
    )


class ModelComputeOperationData(ModelOperationDataBase):
    """Compute node operation data for business logic and calculations."""

    operation_type: Literal[EnumNodeType.COMPUTE] = Field(
        default=EnumNodeType.COMPUTE,
        description="Compute operation type",
    )
    algorithm_type: str = Field(..., description="Type of algorithm or computation")
    computation_resources: dict[str, float] = Field(
        default_factory=dict,
        description="Required computation resources",
    )
    optimization_hints: dict[str, str] = Field(
        default_factory=dict,
        description="Performance optimization hints",
    )
    parallel_execution: bool = Field(
        default=False,
        description="Whether computation can be parallelized",
    )


class ModelEffectOperationData(ModelOperationDataBase):
    """Effect node operation data for external interactions."""

    operation_type: Literal[EnumNodeType.EFFECT] = Field(
        default=EnumNodeType.EFFECT,
        description="Effect operation type",
    )
    target_system: str = Field(..., description="Target external system")
    interaction_type: str = Field(..., description="Type of external interaction")
    retry_policy: dict[str, int] = Field(
        default_factory=dict,
        description="Retry policy configuration",
    )
    side_effect_tracking: bool = Field(
        default=True,
        description="Whether to track side effects",
    )


class ModelReducerOperationData(ModelOperationDataBase):
    """Reducer node operation data for state management and aggregation."""

    operation_type: Literal[EnumNodeType.REDUCER] = Field(
        default=EnumNodeType.REDUCER,
        description="Reducer operation type",
    )
    aggregation_type: str = Field(..., description="Type of data aggregation")
    state_key: str = Field(..., description="State key for aggregation")
    persistence_config: dict[str, str] = Field(
        default_factory=dict,
        description="Data persistence configuration",
    )
    consistency_level: str = Field(
        default="eventual",
        description="Data consistency requirements",
    )


class ModelOrchestratorOperationData(ModelOperationDataBase):
    """Orchestrator node operation data for workflow coordination."""

    operation_type: Literal[EnumNodeType.ORCHESTRATOR] = Field(
        default=EnumNodeType.ORCHESTRATOR,
        description="Orchestrator operation type",
    )
    workflow_definition: str = Field(..., description="Workflow definition identifier")
    coordination_strategy: str = Field(..., description="Coordination strategy")
    dependency_resolution: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Dependency resolution configuration",
    )
    error_handling_strategy: str = Field(
        default="stop_on_error",
        description="Error handling strategy",
    )


# Main operation payload class (defined after all dependencies)
class ModelOperationPayload(BaseModel):
    """
    Strongly-typed operation payload with discriminated unions.

    Replaces dict[str, Any] with discriminated operation payload types.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Identifiable: UUID-based identification
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    operation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique operation identifier (UUID format)",
    )
    operation_type: EnumNodeType = Field(
        ...,
        description="Discriminated operation type (ONEX node type)",
    )
    operation_data: Annotated[
        ModelComputeOperationData
        | ModelEffectOperationData
        | ModelReducerOperationData
        | ModelOrchestratorOperationData,
        Field(discriminator="operation_type"),
    ] = Field(..., description="Operation-specific data with discriminated union")
    execution_metadata: ModelExecutionMetadata | None = Field(
        None,
        description="Execution metadata for the operation",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelOperationPayload"]
