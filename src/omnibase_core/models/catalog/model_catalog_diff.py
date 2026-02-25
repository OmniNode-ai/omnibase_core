# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Catalog diff model — holds diff between old and new catalog after a refresh.

.. versionadded:: 0.19.0  (OMN-2544)
"""

from __future__ import annotations

__all__ = ["ModelCatalogDiff"]


class ModelCatalogDiff:
    """Holds the diff between the old and new catalog after a refresh.

    Attributes:
        added: Command IDs added in the new catalog.
        removed: Command IDs removed in the new catalog.
        updated: Command IDs whose metadata changed.
        deprecated: Command IDs that became deprecated.
    """

    def __init__(
        self,
        added: list[str],
        removed: list[str],
        updated: list[str],
        deprecated: list[str],
    ) -> None:
        self.added = added
        self.removed = removed
        self.updated = updated
        self.deprecated = deprecated

    def is_empty(self) -> bool:
        """Return True when the catalog did not change."""
        return not (self.added or self.removed or self.updated or self.deprecated)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"ModelCatalogDiff("
            f"added={self.added}, removed={self.removed}, "
            f"updated={self.updated}, deprecated={self.deprecated})"
        )
