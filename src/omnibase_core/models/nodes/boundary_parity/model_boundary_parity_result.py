# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The parity verdict for one Kafka boundary."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.nodes.boundary_parity.model_kafka_boundary_entry import (
    ModelKafkaBoundaryEntry,
)

__all__ = ["ModelBoundaryParityResult"]


class ModelBoundaryParityResult(BaseModel):
    """Whether the producer and consumer files of one boundary reference its topic."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    boundary: ModelKafkaBoundaryEntry
    producer_ok: bool
    consumer_ok: bool
    producer_file_exists: bool
    consumer_file_exists: bool
    error: str = ""
