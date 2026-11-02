# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelViewDocument — the rows of one view, sealed (OMN-21997).

A document is what a surface renders: one entry per section, each section a
sealed widget envelope (the config half, covered by the envelope's own seal) and
its rows or a typed empty state. ``document_digest`` covers the whole document
including every row, so an edited row no longer matches it; an edited config
fails the envelope seal. Use ``omnibase_core.models.dashboard.model_view_document_digest``
to seal and verify.

Sections are a union discriminated by ``kind``; each member fixes its
envelope's kind, its config kind and its row model (see
``model_view_section_base``).
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Annotated, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from omnibase_core.models.dashboard.model_view_section_drawer_detail import (
    ModelViewSectionDrawerDetail,
)
from omnibase_core.models.dashboard.model_view_section_freshness import (
    ModelViewSectionFreshness,
)
from omnibase_core.models.dashboard.model_view_section_line_card import (
    ModelViewSectionLineCard,
)
from omnibase_core.models.dashboard.model_view_section_machine_bay import (
    ModelViewSectionMachineBay,
)
from omnibase_core.models.dashboard.model_view_section_stage_progress import (
    ModelViewSectionStageProgress,
)
from omnibase_core.models.dashboard.model_view_section_stop import (
    ModelViewSectionStop,
)
from omnibase_core.models.dashboard.model_view_section_trend import (
    ModelViewSectionTrend,
)
from omnibase_core.models.dashboard.model_view_slug import ViewSlug
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["VIEW_DOCUMENT_DIGEST_PATTERN", "ModelViewDocument", "ModelViewSection"]

#: Seals are ``sha256:<64 lowercase hex chars>``.
VIEW_DOCUMENT_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

#: Sections that report the state of one thing: a line, a bay, a stage, a stop.
_StateSections = (
    ModelViewSectionLineCard
    | ModelViewSectionMachineBay
    | ModelViewSectionStageProgress
    | ModelViewSectionStop
)

#: Sections that report a measurement or its detail.
_MeasureSections = (
    ModelViewSectionFreshness | ModelViewSectionTrend | ModelViewSectionDrawerDetail
)

#: Discriminated union of the seven row-driven section kinds, keyed by ``kind``.
ModelViewSection = Annotated[
    _StateSections | _MeasureSections,
    Field(discriminator="kind"),
]


class ModelViewDocument(BaseModel):
    """The sealed rows of one view at one moment."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    view_id: ViewSlug = Field(..., description="Slug of the view this document renders")
    contract_version: ModelSemVer = Field(
        ..., description="Version of the view contract the document was built from"
    )
    generated_at: AwareDatetime = Field(..., description="When the rows were read")
    sections: tuple[ModelViewSection, ...] = Field(
        ..., min_length=1, description="Sections, in display order"
    )
    document_digest: str = Field(
        ...,
        description=(
            "SHA-256 over this document's canonical JSON excluding this field, "
            "as 'sha256:<hex>'. Covers every row and every envelope."
        ),
    )

    @field_validator("document_digest")
    @classmethod
    def validate_document_digest(cls, value: str) -> str:
        """Reject anything that is not a ``sha256:<hex>`` seal.

        Raises:
            ValueError: If ``value`` does not match the digest pattern.
        """
        if not VIEW_DOCUMENT_DIGEST_PATTERN.match(value):
            raise ValueError(
                f"document_digest must match 'sha256:<64 hex chars>', got '{value}'"
            )
        return value

    @model_validator(mode="after")
    def validate_section_ids_are_distinct(self) -> Self:
        """Refuse two sections with the same id.

        Raises:
            ValueError: If a section id appears more than once.
        """
        repeated = sorted(
            section_id
            for section_id, count in Counter(
                s.section_id for s in self.sections
            ).items()
            if count > 1
        )
        if repeated:
            raise ValueError(f"duplicate section ids: {repeated}")
        return self

    @model_validator(mode="after")
    def validate_rows_belong_to_this_view(self) -> Self:
        """Require every row id to name this view.

        Raises:
            ValueError: If a row names another view.
        """
        for section in self.sections:
            for row in section.rows:
                if row.row_id.view_id != self.view_id:
                    raise ValueError(
                        f"row {row.row_id.as_string()} names view_id "
                        f"'{row.row_id.view_id}' but sits in view '{self.view_id}'"
                    )
        return self
