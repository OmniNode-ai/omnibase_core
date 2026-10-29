# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Findings produced by the transport-import checker."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.transport_import_check.model_transport_import_finding import (
    ModelTransportImportFinding,
)


class ModelTransportImportCheckOutput(BaseModel):
    """Every banned transport import found across the supplied paths."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelTransportImportFinding, ...] = ()
