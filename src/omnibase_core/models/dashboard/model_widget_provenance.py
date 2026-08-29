# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""WidgetProvenance — who published a widget, and from which bytes (OMN-16883).

A widget envelope crosses Plane 1 — the contract plane a marketplace
distributes. A consumer that cannot say *which pack published this and from
which source revision* is trusting the publisher, which is the failure
distributing contracts rather than code exists to avoid.

The source revision is a **full** 40-character git object id on purpose. An
abbreviated revision is ambiguous by construction — it names a prefix, not a
commit — and provenance that cannot be resolved back to exact bytes is
decoration.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelWidgetProvenance", "WIDGET_SOURCE_REVISION_PATTERN"]

#: A full, unabbreviated git object id.
WIDGET_SOURCE_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class ModelWidgetProvenance(BaseModel):
    """Publishing origin of a widget envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    pack_namespace: str = Field(  # string-id-ok: namespaced pack label, not a UUID
        ...,
        description="Namespace that published this widget (e.g. 'onex.packs.platform')",
        min_length=1,
    )
    pack_name: str = Field(  # string-id-ok: semantic pack label, not a UUID
        ...,
        description="Name of the publishing pack within its namespace",
        min_length=1,
    )
    pack_version: ModelSemVer = Field(
        ...,
        description="Version of the publishing pack this widget shipped in",
    )
    source_revision: str = Field(
        ...,
        description=(
            "Full 40-character git object id of the source the pack was built "
            "from. Abbreviated revisions are rejected: they name a prefix, not "
            "a commit."
        ),
        min_length=40,
        max_length=40,
        pattern=WIDGET_SOURCE_REVISION_PATTERN.pattern,
    )

    @field_validator("source_revision")
    @classmethod
    def validate_source_revision(cls, value: str) -> str:
        """Reject anything that is not a full git object id.

        Raises:
            ValueError: If ``value`` is not 40 lowercase hex characters.
        """
        if not WIDGET_SOURCE_REVISION_PATTERN.fullmatch(value):
            raise ValueError(
                f"source_revision must be a full 40-character lowercase git "
                f"object id, got '{value}'"
            )
        return value
