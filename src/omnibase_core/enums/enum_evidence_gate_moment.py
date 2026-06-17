# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""When an evidence requirement gates a UI surface (OMN-13130)."""

from enum import StrEnum

__all__ = ["EnumEvidenceGateMoment"]


class EnumEvidenceGateMoment(StrEnum):
    """The moment at which an evidence requirement is enforced."""

    ON_RENDER = "on-render"
    """Evidence must exist before the panel renders."""

    ON_COMMIT = "on-commit"
    """Evidence must exist before the action commits."""
