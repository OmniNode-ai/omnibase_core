# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelInfrastructureHealth — infrastructure component health snapshot."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_dogfood_status import EnumDogfoodStatus


class ModelInfrastructureHealth(BaseModel):
    """Infrastructure component health snapshot."""

    model_config = ConfigDict(frozen=True)

    kafka: EnumDogfoodStatus = Field(..., description="Kafka (Redpanda) broker health")
    postgres: EnumDogfoodStatus = Field(..., description="PostgreSQL availability")
    docker: EnumDogfoodStatus = Field(
        ..., description="Docker daemon and required container health"
    )
    consumer_groups: EnumDogfoodStatus = Field(
        ..., description="Kafka consumer group lag status"
    )
    status: EnumDogfoodStatus = Field(
        ..., description="Aggregate infrastructure health status"
    )
