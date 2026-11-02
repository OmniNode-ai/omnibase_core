# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Counting the sections and rows of a view document (OMN-21997)."""

from __future__ import annotations

from omnibase_core.enums.enum_view_disposition import EnumViewDisposition
from omnibase_core.models.dashboard.model_view_disposition_count import (
    ModelViewDispositionCount,
)
from omnibase_core.models.dashboard.model_view_document import ModelViewDocument
from omnibase_core.models.dashboard.model_view_document_count import (
    ModelViewDocumentCount,
)

__all__ = ["count_view_document"]


def count_view_document(document: ModelViewDocument) -> ModelViewDocumentCount:
    """Return a document's section ids and row ids by disposition.

    A section with rows is ``POPULATED``; a section with a typed empty state is
    ``EMPTY``. Every disposition is present in the result, in enum order, and
    ids keep document order.

    Args:
        document: The document to count.

    Returns:
        The ids by disposition.
    """
    section_ids: dict[EnumViewDisposition, list[str]] = {
        disposition: [] for disposition in EnumViewDisposition
    }
    row_ids: dict[EnumViewDisposition, list[str]] = {
        disposition: [] for disposition in EnumViewDisposition
    }
    for section in document.sections:
        disposition = (
            EnumViewDisposition.POPULATED if section.rows else EnumViewDisposition.EMPTY
        )
        section_ids[disposition].append(section.section_id)
        row_ids[disposition].extend(row.row_id.as_string() for row in section.rows)
    return ModelViewDocumentCount(
        view_id=document.view_id,
        dispositions=tuple(
            ModelViewDispositionCount(
                disposition=disposition,
                section_ids=tuple(section_ids[disposition]),
                row_ids=tuple(row_ids[disposition]),
            )
            for disposition in EnumViewDisposition
        ),
    )
