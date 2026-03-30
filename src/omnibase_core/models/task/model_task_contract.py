# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Lightweight task contract for agent team verification.

A task contract is a frozen subset of ModelTicketContract, generated per
agent team task. One Linear ticket may spawn N tasks each with their own
contract. Contracts are immutable once generated.
"""

from __future__ import annotations

from datetime import datetime

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.task.model_mechanical_check import ModelMechanicalCheck
from omnibase_core.utils.util_decorators import allow_string_id


@allow_string_id(reason="Task ID is an external identifier (e.g., task-1)")
class ModelTaskContract(BaseModel):
    """Frozen contract for a single agent team task."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    # string-version-ok: lightweight contract; ModelSemVer not warranted here
    schema_version: str = Field(default="1.0.0", description="Contract schema version")
    # string-id-ok: task IDs are external identifiers (e.g., task-1), not UUIDs
    task_id: str = Field(..., description="Task identifier (e.g., task-1)")
    parent_ticket: str | None = Field(
        default=None, description="Parent Linear ticket ID"
    )
    repo: str | None = Field(default=None, description="Target repository")
    branch: str | None = Field(default=None, description="Target branch")
    generated_at: datetime = Field(
        ..., description="When this contract was generated (explicit, no default)"
    )
    generated_by: str = Field(
        default="task_contract_generator",
        description="Generator source/provenance",
    )
    fingerprint: str = Field(
        default="",
        description="SHA-256 of requirements + definition_of_done for identity",
    )
    requirements: list[str] = Field(
        default_factory=list, description="Task requirements"
    )
    definition_of_done: list[ModelMechanicalCheck] = Field(
        default_factory=list,
        description="Mechanical checks that define completion",
    )
    human_checks: list[str] = Field(
        default_factory=list,
        description="Non-mechanical checks that require human or LLM judgment (not gated mechanically)",
    )
    verification_tier: str = Field(
        default="full",
        description="Verification tier: full (A+B quorum) or reduced (A only, mechanical)",
    )

    def to_yaml(self) -> str:
        """Serialize contract to YAML string."""
        data = self.model_dump(mode="json")
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> ModelTaskContract:
        """Deserialize contract from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls(**data)
