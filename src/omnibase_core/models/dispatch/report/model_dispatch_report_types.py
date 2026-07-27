# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared field types and base config for dispatch report models (OMN-15161).

Fleet-generic port of steel_onslaught PR #213's shared field-type aliases and
closed/strict base model (originally
``steel_onslaught.contracts.dispatch_report``).

Field-name-suffix convention (load-bearing for
``omnibase_core.validation.validator_dispatch_report_anchors``): any field
ending ``_sha`` is a git-commit content anchor; any field ending ``_paths``
is a list-of-artifact-paths content anchor. New roles/fields that follow this
convention are picked up by the anchor validator automatically -- no
per-field wiring needed there.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    StringConstraints,
)

__all__ = ["GitSha", "ModelDispatchReportBase", "PrNumber"]

# Git commits are 40-hex-char SHA-1 (or, on a sha256 object-format repo,
# 64-hex-char) object ids; ``git cat-file -e`` also accepts abbreviated
# short SHAs, so the floor is a conservative 7 characters. This is a SHAPE
# check only -- whether the SHA actually resolves to a real commit is a
# content anchor checked by
# ``omnibase_core.validation.validator_dispatch_report_anchors`` against a
# caller-supplied git dir, never here.
GitSha = Annotated[StrictStr, StringConstraints(pattern=r"^[0-9a-f]{7,64}$")]

PrNumber = Annotated[StrictInt, Field(gt=0)]


class ModelDispatchReportBase(BaseModel):
    """Shared closed/strict config for every per-role dispatch report model."""

    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, from_attributes=True
    )
