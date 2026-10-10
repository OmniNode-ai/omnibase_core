# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One Kafka boundary declared in the cross-repo boundary manifest."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

__all__ = ["ModelKafkaBoundary"]


class ModelKafkaBoundary(BaseModel):
    """A producer file and a consumer file that must both reference one topic.

    ``status`` is ``active`` or ``pending``; a pending boundary carries the ISO
    date it became pending and a reason.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic_name: str
    producer_repo: str
    consumer_repo: str
    producer_file: str
    consumer_file: str
    topic_pattern: str
    status: str = "active"
    pending_since: str = ""
    pending_reason: str = ""

    @property
    def producer_path(self) -> str:
        """The producer file as ``<repo>/<repo-relative path>``."""
        return f"{self.producer_repo}/{self.producer_file}"

    @property
    def consumer_path(self) -> str:
        """The consumer file as ``<repo>/<repo-relative path>``."""
        return f"{self.consumer_repo}/{self.consumer_file}"
