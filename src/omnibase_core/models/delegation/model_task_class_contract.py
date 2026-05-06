# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelTaskClassContract: root model for task_class_contract.yaml (OMN-10614)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.delegation.model_task_class_entry import ModelTaskClassEntry


class ModelTaskClassContract(BaseModel):
    """Root model for task_class_contract.yaml.

    Parsed directly from YAML via model_validate(yaml.safe_load(...)). The
    version field is a string to allow future semver expansion without a
    breaking schema change.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    version: str
    task_classes: dict[str, ModelTaskClassEntry] = Field(default_factory=dict)


__all__ = ["ModelTaskClassContract"]
