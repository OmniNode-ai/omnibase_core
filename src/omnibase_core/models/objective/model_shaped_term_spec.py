# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shaped term specification model for objective reward shaping.

Defines a single shaped reward term within an ObjectiveSpec. Shaped terms
are only evaluated when all hard gates pass — they can never override a gate.

Part of the objective functions and reward architecture (OMN-2537).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelShapedTermSpec"]


class ModelShapedTermSpec(BaseModel):
    """Specification for a single shaped reward term in an ObjectiveSpec.

    Shaped terms define the optimization direction and weight for a metric.
    They are applied ONLY when all hard gates pass. A shaped term can never
    override a gate failure.

    Shaping weights must be bounded and explicitly declared. The weight
    determines the relative contribution of this term to the shaped score.

    Attributes:
        id: Unique identifier for this term within the objective.
        weight: Relative contribution weight (must be > 0).
        direction: Whether to maximize or minimize this metric.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    id: str = Field(  # string-id-ok: shaped term identifier within an objective
        description="Unique identifier for this shaped term within the objective spec"
    )
    weight: float = Field(
        gt=0.0,
        description="Relative contribution weight of this term to the shaped score (must be > 0)",
    )
    direction: Literal["maximize", "minimize"] = Field(
        description="Whether to maximize or minimize this metric"
    )
