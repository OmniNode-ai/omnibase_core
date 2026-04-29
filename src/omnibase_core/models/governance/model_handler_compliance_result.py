# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Handler Compliance Result Model.

Single handler audit result for contract compliance checks.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_compliance_verdict import EnumComplianceVerdict
from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)


class ModelHandlerComplianceResult(BaseModel):
    """Audit result for a single handler's contract compliance.

    Captures the cross-reference between a handler's actual behavior
    (topics used, transports imported, routing registration) and what
    is declared in its contract.yaml.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    handler_path: str = Field(
        ...,
        description="Relative path to handler file",
    )
    node_dir: str = Field(
        ...,
        description="Parent node directory",
    )
    repo: str = Field(
        ...,
        description="Repository name",
    )
    contract_path: str | None = Field(
        default=None,
        description="Path to associated contract.yaml (None if missing)",
    )
    violations: list[EnumComplianceViolation] = Field(
        default_factory=list,
        description="Specific violations found",
    )
    violation_details: list[str] = Field(
        default_factory=list,
        description="Human-readable detail per violation",
    )
    declared_topics: list[str] = Field(
        default_factory=list,
        description="Topics declared in contract.yaml",
    )
    used_topics: list[str] = Field(
        default_factory=list,
        description="Topics referenced in handler source code",
    )
    undeclared_topics: list[str] = Field(
        default_factory=list,
        description="Topics used but not declared",
    )
    declared_transports: list[str] = Field(
        default_factory=list,
        description="Transports declared in contract capabilities",
    )
    used_transports: list[str] = Field(
        default_factory=list,
        description="Transports detected in handler imports/calls",
    )
    undeclared_transports: list[str] = Field(
        default_factory=list,
        description="Transports used but not declared",
    )
    handler_in_routing: bool = Field(
        default=False,
        description="Whether handler is registered in contract.yaml handler_routing",
    )
    verdict: EnumComplianceVerdict = Field(
        ...,
        description="Overall compliance verdict",
    )
    allowlisted: bool = Field(
        default=False,
        description="Whether this handler is in the allowlist",
    )
