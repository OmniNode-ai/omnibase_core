# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelEndpointHealth — health record for a single HTTP endpoint probe."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dogfood_status import EnumDogfoodStatus

_MAX_STRING_LENGTH = 10000


class ModelEndpointHealth(BaseModel):
    """Health record for a single HTTP endpoint probe."""

    model_config = ConfigDict(frozen=True)

    path: str = Field(..., description="Endpoint path", max_length=_MAX_STRING_LENGTH)
    http_code: int = Field(..., description="HTTP response status code", ge=100, le=599)
    has_data: bool = Field(
        ..., description="Whether the response body contained meaningful data"
    )
    response_schema_valid: bool = Field(
        ..., description="Whether the response body matched the expected schema"
    )
    status: EnumDogfoodStatus = Field(..., description="Endpoint health status")
