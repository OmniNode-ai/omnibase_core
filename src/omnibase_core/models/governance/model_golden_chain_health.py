# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGoldenChainHealth — health record for a single named golden chain."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dogfood_status import EnumDogfoodStatus

_MAX_STRING_LENGTH = 10000


class ModelGoldenChainHealth(BaseModel):
    """Health record for a single named golden chain."""

    model_config = ConfigDict(frozen=True)

    chain_name: str = Field(
        ...,
        description="Human-readable chain identifier",
        max_length=_MAX_STRING_LENGTH,
    )
    topic: str = Field(
        ..., description="Kafka topic name", max_length=_MAX_STRING_LENGTH
    )
    table: str = Field(
        ..., description="Downstream DB table name", max_length=_MAX_STRING_LENGTH
    )
    row_count: int = Field(
        ..., description="Current row count in the downstream table", ge=0
    )
    status: EnumDogfoodStatus = Field(..., description="Chain health status")
