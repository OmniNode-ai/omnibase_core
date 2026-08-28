# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ThemeCatalog — the set of published theme revisions (OMN-16882, Phase C1).

Resolution of open design item **OD-2** (plan §5.1), recorded here because the
shape of this model *is* the answer:

* **Published revisions are a compiled artifact shipped with the library.** They
  are immutable, content-digested, and byte-reproducible offline, so two
  surfaces can agree on a digest with no service in the path. A registry
  projection cannot give that property to a build input.
* **The active pointer is runtime state, not a catalog field.** Which surface
  renders which revision is mutable, per-surface, and reported — that half is
  ``ModelThemeActivation`` and is served the way every other read is served.

Splitting them is what makes "rollback moves a pointer, and the digest proves
the old bytes came back" mechanically true: the revisions cannot move, and the
pointer carries the digest it resolved.
"""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dashboard.model_theme_catalog_entry import (
    ModelThemeCatalogEntry,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = ["ModelThemeCatalog"]


class ModelThemeCatalog(BaseModel):
    """Every published theme revision, indexed by (theme_id, instance_revision)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    catalog_version: ModelSemVer = Field(
        ...,
        description="Version of the catalog format itself (not of any theme)",
    )
    entries: tuple[ModelThemeCatalogEntry, ...] = Field(
        ...,
        description="Published, immutable theme revisions",
    )

    @model_validator(mode="after")
    def validate_revisions_are_unique(self) -> Self:
        """Reject a catalog that publishes one revision twice.

        A duplicated (theme_id, instance_revision) makes ``entry_for`` ambiguous
        and would let two digests claim the same revision — the exact drift the
        digest axis exists to detect.

        Raises:
            ValueError: If any (theme_id, instance_revision) pair repeats.
        """
        seen: set[tuple[str, str]] = set()
        for entry in self.entries:
            key = (entry.theme_id, str(entry.instance_revision))
            if key in seen:
                raise ValueError(
                    f"duplicate catalog entry for theme '{entry.theme_id}' "
                    f"revision {entry.instance_revision}"
                )
            seen.add(key)
        return self

    def entry_for(
        self, theme_id: str, instance_revision: ModelSemVer
    ) -> ModelThemeCatalogEntry:
        """Resolve one published revision, failing closed when it is absent.

        Args:
            theme_id: Namespaced theme identifier.
            instance_revision: The exact revision to resolve. Consumers pin an
                exact revision; there is deliberately no ``latest``.

        Returns:
            The matching catalog entry.

        Raises:
            ModelOnexError: If no entry matches.
        """
        for entry in self.entries:
            if entry.theme_id == theme_id and entry.instance_revision == (
                instance_revision
            ):
                return entry
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.RESOURCE_NOT_FOUND,
            message=(
                f"theme '{theme_id}' revision {instance_revision} is not published "
                f"in this catalog"
            ),
        )
