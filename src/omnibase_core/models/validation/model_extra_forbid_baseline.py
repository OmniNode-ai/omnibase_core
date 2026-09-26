# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelExtraForbidBaseline — frozen ratchet baseline document (OMN-18038).

Typed contract boundary for ``omnibase_core/validators/extra_forbid_baseline.yaml``,
the shrink-only ratchet behind the ``extra="forbid"`` gate (OMN-14515). The document
is closed — a single ``violations`` list of ``module:ClassName`` strings — so the
model forbids extras: an unexpected key in a ratchet file is a silent ratchet leak,
not a harmless comment.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelExtraForbidBaseline(BaseModel):
    """Parsed ``extra_forbid_baseline.yaml`` document."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    violations: list[str] = Field(
        default_factory=list,
        description="Frozen ``module:ClassName`` FQNs that predate the gate",
    )

    @property
    def fqns(self) -> set[str]:
        """Baselined FQNs as the set the ratchet compares live findings against."""
        return set(self.violations)


__all__ = ["ModelExtraForbidBaseline"]
