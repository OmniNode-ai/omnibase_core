# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ThemeActivation — a surface's active theme pointer (OMN-16882, Phase C1).

Publish adds an immutable revision to the catalog and changes no pixels.
**Activate** is the only step that changes what a surface renders, and it is a
pointer move: this model *is* the pointer.

Each activation carries the ``content_digest`` it resolved from the catalog, so
a surface can report what it is actually rendering (gate G-U1's reporting half)
and a rollback can be proven rather than asserted — the restored activation must
carry the *same digest bytes* as the activation it restores, not merely the same
revision number.

``activation_sequence`` orders activations without a timestamp: ordering here is
a fact about the pointer's history, and a monotonic integer is deterministic
where a clock is not.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.dashboard.model_theme_catalog_entry import (
    THEME_CONTENT_DIGEST_PATTERN,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelThemeActivation"]

#: Reused so the pointer and the entry cannot disagree about digest shape.
_DIGEST_PATTERN: re.Pattern[str] = THEME_CONTENT_DIGEST_PATTERN


class ModelThemeActivation(BaseModel):
    """Which published theme revision a surface is currently rendering."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    surface_id: str = Field(  # string-id-ok: semantic surface label, not a UUID
        ...,
        description="Surface whose active theme this pointer describes (e.g. 'omnidash')",
        min_length=1,
    )
    theme_id: str = Field(  # string-id-ok: namespaced theme label, not a UUID
        ...,
        description="Namespaced theme identifier this surface renders",
        min_length=1,
    )
    instance_revision: ModelSemVer = Field(
        ...,
        description="Exact published revision this surface renders",
    )
    content_digest: str = Field(
        ...,
        description=(
            "Digest resolved from the catalog at activation time. Two surfaces "
            "on one entry must report the same value (GC.2)."
        ),
    )
    activation_sequence: int = Field(
        ...,
        ge=1,
        description="Monotonic activation counter for this surface; first activation is 1",
    )
    superseded_revision: ModelSemVer | None = Field(
        default=None,
        description=(
            "Revision this activation replaced, and therefore the revision a "
            "rollback returns to. None on a surface's first activation."
        ),
    )

    @field_validator("content_digest")
    @classmethod
    def validate_content_digest(cls, value: str) -> str:
        """Reject anything that is not a ``sha256:<hex>`` digest.

        Raises:
            ValueError: If ``value`` does not match the digest pattern.
        """
        if not _DIGEST_PATTERN.match(value):
            raise ValueError(
                f"content_digest must match 'sha256:<64 hex chars>', got '{value}'"
            )
        return value
