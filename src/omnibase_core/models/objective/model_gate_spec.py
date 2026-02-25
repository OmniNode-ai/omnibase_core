# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gate specification model for ObjectiveSpec hard gates.

Defines a single hard gate within an objective. Gates dominate all
shaped terms — a run that fails any gate is a failed run, period.

Part of the objective functions and reward architecture (OMN-2537).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_gate_type import EnumGateType

__all__ = ["ModelGateSpec"]


class ModelGateSpec(BaseModel):
    """Specification for a single hard gate in an ObjectiveSpec.

    Hard gates are binary pass/fail checks evaluated before any shaped
    reward terms. A gate failure causes the entire run to fail with a
    zero ScoreVector, regardless of all other metrics.

    Attributes:
        id: Unique identifier for this gate within the objective.
        type: The gate type (test_pass, budget, latency, etc.).
        threshold: The numeric threshold for pass/fail determination.
        weight: Relative priority among gates for tiebreaking and attribution.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: str = Field(  # string-id-ok: gate identifier within an objective
        description="Unique identifier for this gate within the objective spec"
    )
    type: EnumGateType = Field(description="The type of gate check to perform")
    threshold: float = Field(
        description="Numeric threshold for pass/fail determination (semantics depend on gate type)"
    )
    weight: float = Field(
        gt=0.0,
        description="Relative priority among gates for tiebreaking and attribution (must be > 0)",
    )
