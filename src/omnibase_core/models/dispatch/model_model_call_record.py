# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Model-call record for dispatch evaluation cost accounting."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.cost import ModelCostProvenance


class ModelCallRecord(BaseModel):
    """Single model invocation observed during a dispatch evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    provider: str = Field(description="Model provider name.", min_length=1)
    model: str = Field(description="Provider model identifier.", min_length=1)
    input_tokens: int = Field(description="Input token count.", ge=0)
    output_tokens: int = Field(description="Output token count.", ge=0)
    latency_ms: int = Field(description="Invocation latency in milliseconds.", ge=0)
    cost_dollars: float = Field(description="Invocation cost in dollars.", ge=0)
    cost_provenance: ModelCostProvenance = Field(
        description="Validated provenance for this model call's cost."
    )
