# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from pydantic import BaseModel, ConfigDict, field_validator


class ModelNodeGenerationRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    task_description: str
    correlation_id: str
    target_node_type: str = "compute"
    max_attempts: int = 2
    generation_timeout_seconds: int = 60
    validation_timeout_seconds: int = 15

    @field_validator("target_node_type")
    @classmethod
    def must_be_compute(cls, v: str) -> str:
        if v != "compute":
            raise ValueError("Hackathon MVP only generates COMPUTE nodes")
        return v
