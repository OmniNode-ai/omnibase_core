from pydantic import Field

"""
Thunk Emission Configuration Model - ONEX Standards Compliant.

Defines thunk creation, emission timing, and deferred
execution strategies for workflow coordination.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelActionEmissionConfig(BaseModel):
    """
    Thunk emission patterns and deferred execution rules.

    Defines thunk creation, emission timing, and deferred
    execution strategies for workflow coordination.
    """

    emission_strategy: str = Field(
        default="on_demand",
        description="Thunk emission strategy (on_demand, batch, scheduled, event_driven)",
    )

    batch_size: int = Field(
        default=10,
        description="Batch size for batch emission strategy",
        ge=1,
    )

    max_deferred_thunks: int = Field(
        default=1000,
        description="Maximum number of deferred thunks",
        ge=1,
    )

    execution_delay_ms: int = Field(
        default=0,
        description="Delay before thunk execution in milliseconds",
        ge=0,
    )

    priority_based_emission: bool = Field(
        default=True,
        description="Enable priority-based thunk emission ordering",
    )

    dependency_aware_emission: bool = Field(
        default=True,
        description="Consider dependencies when emitting thunks",
    )

    retry_failed_thunks: bool = Field(
        default=True,
        description="Automatically retry failed thunk executions",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
