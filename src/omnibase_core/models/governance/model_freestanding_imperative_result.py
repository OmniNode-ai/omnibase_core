# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Freestanding Imperative Result Model (OMN-20918).

Audit result for a single freestanding Python module: source code under ``src/`` that
is not a node handler (not under ``node_*/handlers/``). The node/handler contract
scanner cannot see these modules, yet they are where imperative IO debt accumulates
(raw HTTP inference, direct DB connections, hardcoded inference params, subprocess
network ops). This model captures the per-module verdict so the guard can govern all
of ``src/``.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_compliance_verdict import EnumComplianceVerdict
from omnibase_core.enums.governance.enum_compliance_violation import (
    EnumComplianceViolation,
)
from omnibase_core.enums.governance.enum_reachability import EnumReachability
from omnibase_core.models.governance.model_freestanding_imperative_finding import (
    ModelFreestandingImperativeFinding,
)


class ModelFreestandingImperativeResult(BaseModel):
    """Audit result for one freestanding (non-handler) source module."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    module_path: str = Field(
        ...,
        description="Repo-relative path to the scanned module.",
    )
    repo: str = Field(
        ...,
        description="Repository name.",
    )
    findings: list[ModelFreestandingImperativeFinding] = Field(
        default_factory=list,
        description="All imperative-IO findings in the module (suppressed included).",
    )
    verdict: EnumComplianceVerdict = Field(
        ...,
        description="Overall verdict for the module.",
    )
    allowlisted: bool = Field(
        default=False,
        description="Whether this module path is baselined in the allowlist.",
    )
    reachability: EnumReachability = Field(
        default=EnumReachability.LIVE,
        description="Whether this module is reachable from declared live entrypoints.",
    )

    @property
    def active_findings(self) -> list[ModelFreestandingImperativeFinding]:
        """Findings that are not inline-suppressed."""
        return [f for f in self.findings if not f.suppressed]

    @property
    def violations(self) -> list[EnumComplianceViolation]:
        """Distinct active violation kinds, for parity with handler results."""
        seen: list[EnumComplianceViolation] = []
        for finding in self.active_findings:
            if finding.violation not in seen:
                seen.append(finding.violation)
        return seen
