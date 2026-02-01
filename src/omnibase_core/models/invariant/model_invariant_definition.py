"""Detailed definition for an invariant with type-specific config.

Combines the invariant type discriminator with its corresponding
configuration, enabling type-safe validation dispatch.

Thread Safety:
    ModelInvariantDefinition is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_invariant_type import EnumInvariantType
from omnibase_core.models.invariant.model_cost_config import ModelCostConfig
from omnibase_core.models.invariant.model_custom_invariant_config import (
    ModelCustomInvariantConfig,
)
from omnibase_core.models.invariant.model_field_presence_config import (
    ModelFieldPresenceConfig,
)
from omnibase_core.models.invariant.model_field_value_config import (
    ModelFieldValueConfig,
)
from omnibase_core.models.invariant.model_latency_config import ModelLatencyConfig
from omnibase_core.models.invariant.model_schema_invariant_config import (
    ModelSchemaInvariantConfig,
)
from omnibase_core.models.invariant.model_threshold_config import ModelThresholdConfig

# Type alias for the union of all config types
InvariantConfigUnion = (
    ModelSchemaInvariantConfig
    | ModelFieldPresenceConfig
    | ModelFieldValueConfig
    | ModelThresholdConfig
    | ModelLatencyConfig
    | ModelCostConfig
    | ModelCustomInvariantConfig
)

# Mapping from invariant type to expected config class
# This ensures type safety at runtime by validating config matches type
_INVARIANT_TYPE_TO_CONFIG: dict[EnumInvariantType, type[InvariantConfigUnion]] = {
    EnumInvariantType.SCHEMA: ModelSchemaInvariantConfig,
    EnumInvariantType.FIELD_PRESENCE: ModelFieldPresenceConfig,
    EnumInvariantType.FIELD_VALUE: ModelFieldValueConfig,
    EnumInvariantType.THRESHOLD: ModelThresholdConfig,
    EnumInvariantType.LATENCY: ModelLatencyConfig,
    EnumInvariantType.COST: ModelCostConfig,
    EnumInvariantType.CUSTOM: ModelCustomInvariantConfig,
}


class ModelInvariantDefinition(BaseModel):
    """Detailed definition for an invariant with type-specific config.

    Combines the invariant type discriminator with its corresponding
    configuration, enabling type-safe validation dispatch. This model
    is preferred over ModelInvariant when compile-time type safety is
    needed.

    Attributes:
        invariant_type: Type of invariant determining validation strategy.
        config: Type-specific configuration for the invariant. Must match
            the invariant_type (e.g., LATENCY type requires ModelLatencyConfig).

    Raises:
        ValueError: If config type does not match the expected type for
            the given invariant_type.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    invariant_type: EnumInvariantType = Field(
        ...,
        description="Type of invariant determining validation strategy",
    )
    config: InvariantConfigUnion = Field(
        ...,
        description="Type-specific configuration for the invariant",
    )

    @model_validator(mode="after")
    def validate_config_matches_type(self) -> Self:
        """Validate that config type matches the expected type for invariant_type.

        Each invariant_type requires a specific config class:
        - SCHEMA: ModelSchemaInvariantConfig
        - FIELD_PRESENCE: ModelFieldPresenceConfig
        - FIELD_VALUE: ModelFieldValueConfig
        - THRESHOLD: ModelThresholdConfig
        - LATENCY: ModelLatencyConfig
        - COST: ModelCostConfig
        - CUSTOM: ModelCustomInvariantConfig

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If config type does not match expected type.
        """
        expected_config_type = _INVARIANT_TYPE_TO_CONFIG.get(self.invariant_type)

        if expected_config_type is None:
            # Unknown invariant type - allow any config for extensibility
            return self

        if not isinstance(self.config, expected_config_type):
            actual_type_name = type(self.config).__name__
            expected_type_name = expected_config_type.__name__
            # error-ok: Pydantic model_validator requires ValueError
            raise ValueError(
                f"Config type mismatch for invariant_type '{self.invariant_type.value}': "
                f"expected {expected_type_name}, got {actual_type_name}. "
                f"Each invariant type requires its corresponding config class. "
                f"For {self.invariant_type.value}, use {expected_type_name}."
            )

        return self


__all__ = [
    "InvariantConfigUnion",
    "ModelInvariantDefinition",
]
