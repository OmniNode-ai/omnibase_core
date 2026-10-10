# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One Kafka boundary declaration of the boundary manifest."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelKafkaBoundaryEntry"]


class ModelKafkaBoundaryEntry(BaseModel):
    """A topic that crosses from a producer repository to a consumer repository.

    producer_file and consumer_file are relative to their repository
    root. topic_pattern is a regular expression that must match somewhere in
    each file. status is active or pending; a pending entry is
    skipped while pending_since (YYYY-MM-DD) is within the grace period.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic_name: str
    producer_repo: str
    consumer_repo: str
    producer_file: str
    consumer_file: str
    topic_pattern: str
    event_schema: str = ""
    status: str = "active"
    pending_since: str = ""
    pending_reason: str = ""
