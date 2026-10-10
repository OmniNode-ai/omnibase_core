# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Explicit snapshot supplied to the pure Kafka boundary parity check."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

__all__ = ["ModelBoundaryParityInput"]


class ModelBoundaryParityInput(BaseModel):
    """What the boundary parity check decides over, without filesystem access.

    ``files`` holds the producer and consumer files the manifest names that
    exist, each with a ``<repo>/<repo-relative path>`` POSIX path. A manifest
    file absent from ``files`` is a missing file. ``today`` is the date a
    ``pending`` boundary's grace period is measured against.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    manifest_yaml: str
    files: list[ModelSourceFile] = Field(default_factory=list)
    today: date
