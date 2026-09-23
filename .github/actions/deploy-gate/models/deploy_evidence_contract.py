# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Standalone typed projection used by the reusable deploy-gate script."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from models.deploy_evidence_item import (
    ModelDeployEvidenceItem,
)


class ModelDeployEvidenceContract(BaseModel):
    """Ticket-contract fields inspected by deploy-evidence detection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dod_evidence: list[ModelDeployEvidenceItem] = Field(default_factory=list)

    @classmethod
    def from_yaml(cls, content: str) -> ModelDeployEvidenceContract:
        """Parse YAML safely and validate the typed deploy-evidence projection."""
        import yaml

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise ValueError(f"ticket contract YAML is invalid: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("ticket contract root must be a mapping")
        # This action consumes only the DoD evidence projection from the wider
        # ticket contract. Validate that projection strictly without pretending
        # this standalone helper owns the complete ticket-contract schema.
        return cls.model_validate({"dod_evidence": data.get("dod_evidence", [])})


__all__ = ["ModelDeployEvidenceContract"]
