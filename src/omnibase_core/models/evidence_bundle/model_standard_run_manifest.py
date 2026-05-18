# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelStandardRunManifest — declares what an evidence bundle run covers."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ModelStandardRunManifest(BaseModel):
    """Top-level manifest for a single evidence bundle run.

    Declares correlation identity, runner, timing, and which artifact files
    are expected. Consumers use ``expected_artifacts`` to verify all canonical
    files are present before treating a bundle as complete.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: str
    runner: str
    started_at: datetime
    completed_at: datetime | None = None
    expected_artifacts: tuple[str, ...] = ()
    ticket_id: str | None = None


__all__ = ["ModelStandardRunManifest"]
