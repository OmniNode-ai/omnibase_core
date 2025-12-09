"""
Event Bus Configuration Model.

Event bus configuration for RuntimeHost contract.
MVP implementation with kind only. Advanced event bus configuration
(topics, partitions, serialization) deferred to Beta.

Part of the "one model per file" convention for clean architecture.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelRuntimeEventBusConfig(BaseModel):
    """
    Event bus configuration for RuntimeHost contract.

    MVP implementation with kind only.
    Advanced event bus configuration deferred to Beta.
    """

    kind: str = Field(
        ...,
        description="Event bus kind (e.g., 'kafka', 'local', 'redis')",
        min_length=1,
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )
