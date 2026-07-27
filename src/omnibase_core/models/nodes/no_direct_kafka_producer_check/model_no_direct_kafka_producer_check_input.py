# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the no_direct_kafka_producer_check COMPUTE node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)

__all__ = ["ModelNoDirectKafkaProducerCheckInput"]


class ModelNoDirectKafkaProducerCheckInput(BaseModel):
    """Request to AST-scan a set of (path, source) pairs for direct Kafka producer usage."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    files: list[ModelSourceFile] = Field(default_factory=list)
