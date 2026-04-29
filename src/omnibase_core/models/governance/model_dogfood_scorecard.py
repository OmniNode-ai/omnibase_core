# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDogfoodScorecard — platform dogfood scorecard, a single timestamped health snapshot."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dogfood_status import EnumDogfoodStatus
from omnibase_core.models.governance.model_delegation_health import (
    ModelDelegationHealth,
)
from omnibase_core.models.governance.model_dogfood_regression import (
    ModelDogfoodRegression,
)
from omnibase_core.models.governance.model_endpoint_health import ModelEndpointHealth
from omnibase_core.models.governance.model_golden_chain_health import (
    ModelGoldenChainHealth,
)
from omnibase_core.models.governance.model_infrastructure_health import (
    ModelInfrastructureHealth,
)
from omnibase_core.models.governance.model_readiness_dimension import (
    ModelReadinessDimension,
)

_MAX_STRING_LENGTH = 10000
_MAX_LIST_ITEMS = 500

__all__ = [
    "ModelDogfoodScorecard",
    "ModelDelegationHealth",
    "ModelDogfoodRegression",
    "ModelEndpointHealth",
    "ModelGoldenChainHealth",
    "ModelInfrastructureHealth",
    "ModelReadinessDimension",
]


class ModelDogfoodScorecard(BaseModel):
    """Platform dogfood scorecard — a single timestamped health snapshot."""

    model_config = ConfigDict(frozen=True)

    # string-version-ok: wire type serialized to YAML/JSON at scorecard boundary
    schema_version: str = Field(
        default="1.0.0", description="Scorecard schema version (SemVer)", max_length=20
    )
    captured_at: str = Field(
        ...,
        description="ISO 8601 timestamp when this scorecard was captured",
        max_length=30,
    )
    run_id: str = Field(
        ...,
        description="Unique identifier for this scorecard run",
        max_length=_MAX_STRING_LENGTH,
    )
    readiness_dimensions: list[ModelReadinessDimension] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    golden_chains: list[ModelGoldenChainHealth] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    endpoints: list[ModelEndpointHealth] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    delegation: ModelDelegationHealth | None = Field(default=None)
    infrastructure: ModelInfrastructureHealth | None = Field(default=None)
    regressions: list[ModelDogfoodRegression] = Field(
        default_factory=list, max_length=_MAX_LIST_ITEMS
    )
    overall_status: EnumDogfoodStatus = Field(
        ..., description="Aggregate health status across all dimensions"
    )
