# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Slug type for view and section identifiers (OMN-21997)."""

from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

__all__ = ["VIEW_SLUG_PATTERN", "ViewSlug"]

#: Lowercase alphanumeric words joined by single ``-`` or ``_``.
VIEW_SLUG_PATTERN = r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$"

#: A view or section identifier. A slug, so it is stable in a URL, a row id and
#: a file name; spaces, capitals and punctuation are refused.
ViewSlug = Annotated[str, StringConstraints(pattern=VIEW_SLUG_PATTERN, max_length=64)]
