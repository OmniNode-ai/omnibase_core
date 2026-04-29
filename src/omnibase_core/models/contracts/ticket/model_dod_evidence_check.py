# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDodEvidenceCheck — a single check entry within a DoD evidence item. OMN-8916

OMN-10066 / OMN-9582: Extended to match OCC ModelDodCheck field shapes:
  - check_value now accepts str | dict[str, str] (dict form used by 'grep' check type)
  - cwd field added (OMN-10078): optional working directory for check execution,
    supports ${OMNI_HOME}, ${PR_NUMBER}, ${REPO}, ${TICKET_ID} template tokens
    that the runner substitutes at execution time.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_MAX_STRING_LENGTH = 10000  # DoS prevention, matching OCC constraint


class ModelDodEvidenceCheck(BaseModel):
    """A single verifiable check within a DoD evidence item.

    check_value accepts either a plain string (used by most check types) or a
    dict with string keys/values (used by the 'grep' check type to declare
    both 'pattern' and 'path'). The runner interprets the value per check_type.

    cwd (OMN-10078): optional working directory the runner should use when
    executing this check. Supports ${OMNI_HOME}, ${PR_NUMBER}, ${REPO},
    ${TICKET_ID} template tokens. When omitted the runner inherits its caller's
    cwd. This replaces the brittle ``cd ${OMNI_HOME}/<repo> && `` shell prefix.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    check_type: str = Field(..., min_length=1)
    check_value: str | dict[str, str] = Field(
        ...,
        description="Check-type-specific value (string, command, URL, or pattern dict)",
    )
    cwd: str | None = Field(
        default=None,
        description=(
            "Optional working directory for the check command. Supports "
            "${OMNI_HOME}, ${PR_NUMBER}, ${REPO}, ${TICKET_ID} template "
            "tokens that the runner substitutes at execution time. When "
            "omitted the runner inherits its caller's cwd."
        ),
        max_length=_MAX_STRING_LENGTH,
    )


__all__ = ["ModelDodEvidenceCheck"]
