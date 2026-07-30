# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Execution audience for a ticket contract DoD evidence item (OMN-15392)."""

from __future__ import annotations

from enum import StrEnum


class EnumDodEvidenceExecutionScope(StrEnum):
    """Declare which contract gate is authorized to execute an evidence item.

    ``HOSTED_AND_LOCAL`` is the backwards-compatible default.  It permits the
    hosted contract-compliance gate and the local Done gate to execute the
    item's checks. ``LOCAL_DONE_GATE`` is reserved for checks whose evidence
    source is unavailable to hosted CI, such as a private repository. Hosted
    consumers must report these items as not evaluated; they must never infer a
    passing result from the declaration.
    """

    HOSTED_AND_LOCAL = "hosted_and_local"
    LOCAL_DONE_GATE = "local_done_gate"


__all__ = ["EnumDodEvidenceExecutionScope"]
