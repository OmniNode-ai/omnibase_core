# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The pin policy overlay of the dependency-pin check (OMN-22360).

Loaded from ``contracts/dependency_pin_policy.yaml`` or from a file or an
in-memory document the caller passes. The layer order is the separate
``contracts/repo_layers.yaml`` overlay (``ModelRepoLayerMap``); this document
holds every other value the check judges by.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.models.dependency_pins.model_dependency_pin_hook_repo import (
    ModelDependencyPinHookRepo,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_hook_rev_override import (
    ModelDependencyPinHookRevOverride,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_style_override import (
    ModelDependencyPinStyleOverride,
)

__all__ = ["ModelDependencyPinPolicy"]

DependencyTable = Literal["project", "optional", "group", "uv_dev", "override"]


class ModelDependencyPinPolicy(BaseModel):
    """Which declarations are dependency edges, and the bounds a pin must keep.

    Attributes:
        edge_tables: The pyproject tables whose first-party entries are dependency edges:
            ``project`` (``[project] dependencies``), ``optional`` (extras), ``group``
            (``[dependency-groups]``), ``uv_dev`` (``[tool.uv] dev-dependencies``) and
            ``override`` (``[tool.uv] override-dependencies``).
        pin_style: The pin style every first-party edge must have unless overridden.
        pin_style_overrides: Distributions with a different style.
        release_tag_pattern: A release tag; named group ``version`` is the version.
        tag_inventory_url: The clone URL of a repository; fields ``org`` and ``repo``.
        max_releases_behind: How many releases newer than the pinned version may exist.
        specifier_must_admit_newest_release: Refuse a specifier the newest release does
            not satisfy.
        hook_repos: The pre-commit hook repositories whose pinned revisions are bounded.
        hook_rev_max_releases_behind: How many release tags of the hook repository may be
            newer than a pinned hook revision.
        hook_rev_overrides: Revisions held on purpose, each with its own bound, the
            ticket that removes the hold and the reason the newer revision cannot be
            taken. Keyed on the held sha's abbreviation and matched as a prefix, so an
            override retires itself when the block moves.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    edge_tables: tuple[DependencyTable, ...] = Field(min_length=1)
    pin_style: Literal["range", "exact"]
    pin_style_overrides: tuple[ModelDependencyPinStyleOverride, ...] = ()
    release_tag_pattern: str = Field(min_length=1)
    tag_inventory_url: str = Field(min_length=1)
    max_releases_behind: int = Field(ge=0)
    specifier_must_admit_newest_release: bool
    hook_repos: tuple[ModelDependencyPinHookRepo, ...] = ()
    hook_rev_max_releases_behind: int = Field(ge=0)
    hook_rev_overrides: tuple[ModelDependencyPinHookRevOverride, ...] = ()

    @field_validator("release_tag_pattern")
    @classmethod
    def _has_version_group(cls, value: str) -> str:
        if "(?P<version>" not in value:
            raise ValueError("release_tag_pattern needs a named group 'version'")
        return value

    @model_validator(mode="after")
    def _overrides_only_loosen(self) -> ModelDependencyPinPolicy:
        """An override may not tighten the default, and may not repeat a revision."""
        seen: set[str] = set()
        for override in self.hook_rev_overrides:
            if override.max_releases_behind < self.hook_rev_max_releases_behind:
                raise ValueError(
                    f"hook_rev_overrides[{override.rev_prefix}].max_releases_behind "
                    f"{override.max_releases_behind} is below the default "
                    f"{self.hook_rev_max_releases_behind}; an override states a "
                    "deliberate hold, it does not tighten one block"
                )
            if override.rev_prefix in seen:
                raise ValueError(
                    f"hook_rev_overrides names {override.rev_prefix} twice"
                )
            seen.add(override.rev_prefix)
        return self

    def hook_rev_bound_for(self, rev: str) -> int:
        """The release-count bound that applies to the pinned revision ``rev``."""
        for override in self.hook_rev_overrides:
            if rev.startswith(override.rev_prefix):
                return override.max_releases_behind
        return self.hook_rev_max_releases_behind

    def style_for(self, distribution: str) -> Literal["range", "exact"]:
        """The pin style the policy wants for ``distribution``."""
        for override in self.pin_style_overrides:
            if override.distribution == distribution:
                return override.style
        return self.pin_style
