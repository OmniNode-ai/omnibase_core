# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelZonePolicy — per-zone QA gate configuration (OMN-10354)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_file_zone import EnumFileZone

QaDepth = Literal["full", "standard", "light", "skip"]


class ModelZonePolicy(BaseModel):
    """Frozen per-zone QA gate policy.

    Distinct from agent safety models — this governs per-file-zone QA
    requirements (lint, test, review, security scan) and depth, not
    agent capability gates.
    """

    model_config = ConfigDict(frozen=True)

    zone: EnumFileZone
    qa_depth: QaDepth
    requires_lint: bool
    requires_test: bool
    requires_review: bool
    requires_security_scan: bool
