# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodEvidenceCheck — a single check entry within a DoD evidence item. OMN-8916, OMN-10241"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CheckType = Literal[
    "test_exists",
    "test_passes",
    "file_exists",
    "grep",
    "command",
    "endpoint",
    "behavior_proven",
    "rendered_output",
    "runtime_sha_match",
    "command_exit_0",
]


class ModelDodEvidenceCheck(BaseModel):
    """A single verifiable check within a DoD evidence item.

    check_type must be one of: test_exists, test_passes, file_exists, grep, command, endpoint.
    check_value is either a plain string command/path or a dict[str, str] for structured checks (e.g. grep pattern+path).
    cwd supports template tokens: ${OMNI_HOME}, ${PR_NUMBER}, ${REPO}, ${TICKET_ID}.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_type: CheckType
    check_value: str | dict[str, str]
    cwd: str | None = Field(
        default=None,
        description="Optional working directory. Supports ${OMNI_HOME}, ${PR_NUMBER}, ${REPO}, ${TICKET_ID} tokens.",
    )


__all__ = ["ModelDodEvidenceCheck"]
