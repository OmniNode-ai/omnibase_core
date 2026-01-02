"""Detailed definition for an invariant with type-specific config.

Combines the invariant type discriminator with its corresponding
configuration, enabling type-safe validation dispatch.
"""

from pydantic import BaseModel, ConfigDict, Field

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


__all__ = [
    "InvariantConfigUnion",
    "ModelInvariantDefinition",
]
