# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ModelActivationScope — manifest-level plugin load decision.

Activation is the outermost gate: it decides whether a plugin (hook package
or skill collection) is loaded at all for the current session. This is
distinct from applicability (per-artifact does-this-apply) and enforcement
(what-happens-when-it-applies).

A plugin whose activation scope is not satisfied is never loaded. Its hooks
and skills are not registered. No further scope evaluation occurs.

Plugin manifest example:

.. code-block:: yaml

    activation_scope:
      requires_tokens: [omninode_repo]
      requires_env: [OMNI_HOME]
      requires_integrations:
        linear:
          workspace: omninode
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_scope_token import EnumScopeToken


class ModelActivationScope(BaseModel):
    """
    Manifest-level gate controlling whether a plugin loads for this session.

    Evaluated once at session start by the overlay loader (OMN-9905) and by
    the plugin activation gate (OMN-10044). A plugin is loaded only when all
    declared requirements are satisfied simultaneously.

    Semantics:
        - ``requires_tokens``: ALL listed tokens must match the resolved cwd
          token for the session. Empty list means "always load."
        - ``requires_env``: ALL listed env var names must be set (non-empty)
          in the session environment. Empty list means "no env requirement."
        - ``requires_integrations``: ALL declared integrations must be
          available and match the given key/value filters.

    Activation vs Applicability:
        Activation is manifest-level and coarse-grained — it applies to the
        entire plugin. Applicability (see :class:`~omnibase_core.models.scope.model_applicability_scope.ModelApplicabilityScope`)
        is per-artifact and fine-grained. A hook can be activated (plugin
        loaded) but still be non-applicable (predicate fails for this tool
        event).

    Attributes:
        requires_tokens:       Topology class tokens that must match cwd.
        requires_env:          Env var names that must be set.
        requires_integrations: Named integrations that must be available.

    Example YAML surface:

    .. code-block:: yaml

        activation_scope:
          requires_tokens: [omninode_repo]
          requires_env: [OMNI_HOME, ONEX_STATE_DIR]
          requires_integrations:
            linear:
              workspace: omninode

    See Also:
        - :class:`~omnibase_core.enums.enum_scope_token.EnumScopeToken`:
          Named topology classes for token matching.
        - :class:`~omnibase_core.models.scope.model_enforcement_scope.ModelEnforcementScope`:
          Parent scope model that nests activation, applicability, and enforcement.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    requires_tokens: list[EnumScopeToken] = Field(
        default_factory=list,
        description=(
            "All listed topology tokens must match the resolved cwd token. "
            "Empty list means the plugin loads in any context."
        ),
    )
    requires_env: list[str] = Field(
        default_factory=list,
        description=(
            "All listed environment variable names must be set (non-empty). "
            "Empty list means no environment requirement."
        ),
    )
    requires_integrations: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description=(
            "Named integrations that must be available. Keys are integration "
            "names ('linear', 'kafka'); values are key/value filter maps."
        ),
    )

    def is_unrestricted(self) -> bool:
        """Return True if the plugin loads in any context (no requirements)."""
        return (
            not self.requires_tokens
            and not self.requires_env
            and not self.requires_integrations
        )


__all__ = ["ModelActivationScope"]
