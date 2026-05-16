# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelGenerationReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID
    task_description: str
    generated_contract_hash: str
    generated_handler_hash: str
    validation_result_id: UUID
    model_used: str
    provider: str
    attempts: int
    mcp_tool_name: str
    contract_version: ModelSemVer
    invocation_result_hash: str
