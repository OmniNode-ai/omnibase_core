# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Result of counting a view document (OMN-21997)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_view_disposition import EnumViewDisposition
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_view_disposition_count import (
    ModelViewDispositionCount,
)
from omnibase_core.models.dashboard.model_view_slug import ViewSlug

__all__ = ["ModelViewDocumentCount"]


class ModelViewDocumentCount(BaseModel):
    """Section ids and row ids of a document, by disposition.

    Every disposition is present, including those with nothing in them: a
    document with no empty sections says so rather than omitting the entry.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    view_id: ViewSlug = Field(..., description="Slug of the counted view")
    dispositions: tuple[ModelViewDispositionCount, ...] = Field(
        ..., description="One entry per disposition, in enum order"
    )

    def by_disposition(
        self, disposition: EnumViewDisposition
    ) -> ModelViewDispositionCount:
        """Return the entry for ``disposition``.

        Raises:
            ModelOnexError: If the count holds no entry for it, which
                construction by ``count_view_document`` makes unreachable.
        """
        for entry in self.dispositions:
            if entry.disposition is disposition:
                return entry
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.INVALID_STATE,
            message=f"count holds no entry for disposition '{disposition.value}'",
        )
