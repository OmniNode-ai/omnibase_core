"""
Handler Configuration Model.

Handler configuration for RuntimeHost contract providing handler type
classification for handler registry operations.

MVP implementation with handler type only.
Retry policies and rate limits deferred to Beta.

Strict typing is enforced - no Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_handler_type import EnumHandlerType


class ModelRuntimeHandlerConfig(BaseModel):
    """
    Handler configuration for RuntimeHost contract.

    Defines the handler type classification for handler registry operations.
    MVP implementation provides handler type only.

    Retry policies and rate limits deferred to Beta.
    """

    handler_type: EnumHandlerType = Field(
        ...,
        description="Handler type classification for this configuration",
    )

    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=False,
        validate_assignment=True,
    )
