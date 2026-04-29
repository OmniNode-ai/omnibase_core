# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Migration Spec Model.

Migration plan for a single handler's imperative-to-declarative transition.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)
from omnibase_core.enums.governance.enum_migration_status import EnumMigrationStatus


class ModelMigrationSpec(BaseModel):
    """Migration plan for one handler.

    Captures the violations to fix, specific contract.yaml changes needed,
    handler code changes, and current migration status.

    Lifecycle: PENDING -> GENERATED -> VALIDATED -> DEPLOYED -> RETIRED
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_path: str = Field(..., description="Path to imperative handler")
    node_dir: str = Field(..., description="Parent node directory")
    contract_path: str = Field(
        ..., description="Path to contract.yaml (existing or to-be-created)"
    )
    violations: list[EnumComplianceViolation] = Field(
        default_factory=list, description="Violations to fix"
    )
    contract_changes: list[str] = Field(
        default_factory=list, description="Specific contract.yaml changes needed"
    )
    handler_changes: list[str] = Field(
        default_factory=list, description="Specific handler changes needed"
    )
    estimated_complexity: int = Field(
        ...,
        description="1-5 scale based on violation count and type",
        ge=1,
        le=5,
    )
    status: EnumMigrationStatus = Field(
        default=EnumMigrationStatus.PENDING, description="Current migration status"
    )
    ticket_id: str | None = Field(
        default=None, description="Linear ticket ID tracking this migration"
    )
