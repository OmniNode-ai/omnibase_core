# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Catalog Policy Model — policy filters for Command Catalog materialization.

A ``ModelCatalogPolicy`` instance is passed to ``ServiceCatalogManager`` at
construction time.  All policy filtering is applied once at catalog load time
(not at command invocation time) per the OMN-2544 spec.

Design decisions:
- Policy evaluation is pluggable: supply a custom ``ModelCatalogPolicy`` to
  override any default.  The default implementation (all fields None / empty)
  is permissive — it passes every command through.
- Commands blocked by policy are *hidden entirely*, not merely disabled.
- Allowlist takes priority over denylist: if a command ID appears in both,
  it is visible.
- ``cli_version`` controls minimum version compatibility; commands that
  declare a higher minimum version than the running CLI are hidden.

.. versionadded:: 0.19.0  (OMN-2544)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCatalogPolicy"]


class ModelCatalogPolicy(BaseModel):
    """Policy configuration for catalog command filtering.

    All fields are optional and additive. The default instance is permissive
    (no filtering applied).

    Attributes:
        allowed_roles: If non-empty, a command is visible only when its
            ``permissions`` list intersects this set.  Empty means no
            role-based filtering.
        org_policy_tags: Org-level policy tags.  Commands whose
            ``permissions`` list intersects ``blocked_org_tags`` are hidden.
        blocked_org_tags: Policy tags that cause a command to be hidden.
        allowed_environments: If non-empty, only these environment strings
            are considered in-scope.  Use ``None`` / empty for all envs.
        enabled_feature_flags: Feature flags that must be present for
            experimental commands to be visible.  Experimental commands not
            covered by any enabled flag are hidden.
        hide_deprecated: When True, commands with
            ``visibility == DEPRECATED`` are hidden.  Defaults to False.
        hide_experimental: When True, commands with
            ``visibility == EXPERIMENTAL`` are hidden.  Defaults to False.
        command_allowlist: Explicit allowlist of command IDs.  When
            non-empty, *only* these commands are returned (plus any that
            would pass other filters).  Takes priority over denylist.
        command_denylist: Explicit denylist of command IDs.  Commands in
            this set are hidden unless also in ``command_allowlist``.
        cli_version: The running CLI version string (``MAJOR.MINOR.PATCH``).
            Commands declaring a higher minimum version are hidden.
            ``None`` disables version filtering entirely.
    """

    allowed_roles: set[str] = Field(
        default_factory=set,
        description="Roles that grant visibility. Empty = no role filter.",
    )
    blocked_org_tags: set[str] = Field(
        default_factory=set,
        description="Org policy tags that cause a command to be hidden.",
    )
    allowed_environments: set[str] = Field(
        default_factory=set,
        description="Environments in scope. Empty = all environments.",
    )
    enabled_feature_flags: set[str] = Field(
        default_factory=set,
        description="Feature flags active in this deployment.",
    )
    hide_deprecated: bool = Field(
        default=False,
        description="When True, DEPRECATED commands are hidden.",
    )
    hide_experimental: bool = Field(
        default=False,
        description="When True, EXPERIMENTAL commands are hidden.",
    )
    command_allowlist: set[str] = Field(
        default_factory=set,
        description="Explicit allowlist. Takes priority over denylist.",
    )
    command_denylist: set[str] = Field(
        default_factory=set,
        description="Explicit denylist. Allowlist overrides.",
    )
    cli_version: str | None = Field(
        default=None,
        description=(
            "Running CLI version (MAJOR.MINOR.PATCH). None disables version-gating."
        ),
    )

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )
