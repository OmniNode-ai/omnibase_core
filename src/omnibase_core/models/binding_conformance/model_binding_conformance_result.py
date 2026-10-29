# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Verdict of one check_bindings run."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.binding_conformance.model_binding_conformance_issue import (
    ModelBindingConformanceIssue,
)


class ModelBindingConformanceResult(BaseModel):
    """Conforming only when every checked node produced no issue."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    conforming: bool
    checked_nodes: tuple[str, ...]
    issues: tuple[ModelBindingConformanceIssue, ...]
