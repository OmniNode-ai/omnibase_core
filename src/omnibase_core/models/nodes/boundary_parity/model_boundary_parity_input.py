# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit snapshot supplied to the pure boundary parity handler."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.boundary_parity.model_kafka_boundary_entry import (
    ModelKafkaBoundaryEntry,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

__all__ = ["ModelBoundaryParityInput"]


class ModelBoundaryParityInput(BaseModel):
    """What the parity handler decides over, without filesystem or clock access.

    files holds the producer and consumer files that exist, each keyed by
    <repo>/<repository-relative path>; a declared file absent from
    files is reported missing. now is the timezone-aware instant the
    pending grace period is measured against.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    boundaries: list[ModelKafkaBoundaryEntry] = Field(default_factory=list)
    files: list[ModelSourceFile] = Field(default_factory=list)
    now: datetime
