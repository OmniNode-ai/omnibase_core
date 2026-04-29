# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDayOpenFinding — individual finding from morning investigation."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_finding_severity import EnumFindingSeverity

_MAX_STRING_LENGTH = 10000


class ModelDayOpenFinding(BaseModel):
    """Individual finding from morning investigation."""

    model_config = ConfigDict(frozen=True)

    finding_id: str = Field(  # string-id-ok: stable probe fingerprint slug ({probe}:{category}:{key}), not a DB UUID
        ...,
        description="Stable fingerprint: {probe_name}:{category}:{deterministic_key}",
        max_length=_MAX_STRING_LENGTH,
    )
    severity: EnumFindingSeverity = Field(
        ..., description="Severity level of the finding"
    )
    source_probe: str = Field(
        ...,
        description="Name of the probe that generated this finding",
        max_length=_MAX_STRING_LENGTH,
    )
    title: str = Field(
        ...,
        description="Short description of the finding",
        max_length=_MAX_STRING_LENGTH,
    )
    detail: str = Field(
        default="",
        description="Detailed explanation of the finding",
        max_length=_MAX_STRING_LENGTH,
    )
    repo: str | None = Field(
        default=None,
        description="Affected repository, or None for platform-wide issues",
        max_length=_MAX_STRING_LENGTH,
    )
    suggested_action: str | None = Field(
        default=None,
        description="Recommended action to address the finding",
        max_length=_MAX_STRING_LENGTH,
    )
