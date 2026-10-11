# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Repo-level imperative-contract scan summary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.imperative_contract_guard.model_imperative_contract_guard_report import (
    ModelImperativeContractGuardReport,
)

__all__ = ["ModelImperativeRepoSummary"]


class ModelImperativeRepoSummary(BaseModel):
    """One scanned repository: where it was read, its allowlist and its report."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repository directory name (the report label).")
    repo_root: str
    allowlist_path: str | None = None
    report: ModelImperativeContractGuardReport

    @property
    def handler_count(self) -> int:
        """Handlers audited."""
        return len(self.report.results)

    def to_json(self) -> dict[str, object]:
        """Return JSON-serializable summary data."""
        report = self.report
        return {
            "repo": self.repo,
            "repo_root": self.repo_root,
            "allowlist_path": self.allowlist_path,
            "node_count": report.node_count,
            "handler_count": self.handler_count,
            "compliant_count": report.compliant_count,
            "allowlisted_count": report.allowlisted_count,
            "new_violation_count": report.new_violation_count,
            "non_live_violation_count": report.non_live_violation_count,
            "freestanding_scanned": report.freestanding_scanned,
            "freestanding_module_count": report.freestanding_module_count,
            "new_violations": [
                r.model_dump(mode="json") for r in report.blocking_results
            ],
            "non_live_violations": [
                r.model_dump(mode="json") for r in report.non_live_results
            ],
            "freestanding_violations": [
                r.model_dump(mode="json") for r in report.blocking_freestanding
            ],
            "non_live_freestanding_violations": [
                r.model_dump(mode="json") for r in report.non_live_freestanding
            ],
        }
