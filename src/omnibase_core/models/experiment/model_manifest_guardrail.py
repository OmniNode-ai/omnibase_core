# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""A guardrail bound frozen into a manifest (OMN-22001)."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_guardrail_direction import EnumGuardrailDirection


class ModelManifestGuardrail(BaseModel):
    """One metric that must stay on the acceptable side of a bound.

    Attributes:
        metric: Metric the guardrail watches.
        bound: The bound.
        direction: Which side of the bound is acceptable.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    metric: str = Field(min_length=1)
    bound: float = Field(ge=0.0)
    direction: EnumGuardrailDirection
