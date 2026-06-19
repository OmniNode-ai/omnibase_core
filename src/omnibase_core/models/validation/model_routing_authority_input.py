# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed input payload for the routing-authority COMPUTE validator (OMN-13285).

The routing-authority validator is a pure COMPUTE handler over its envelope
``payload``. The handler MUST NOT read the filesystem itself; the runner /
EFFECT boundary loads every demo-path contract, demo-path source, residue
source, bifrost-config text, and delegation-profile mapping and supplies them as
``ModelRoutingAuthorityInput``. This keeps the validator deterministic and
testable against fixtures with no I/O inside ``handle``.

This is the canonical replacement for the omnimarket-local
``scripts/ci/check_routing_authority.py`` (deleted in the same change) and the
unwired ``validator_delegation_profile`` (folded in as the ``delegation-profile``
rule set).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_routing_authority_file import (
    ModelRoutingAuthorityFile,
)
from omnibase_core.models.validation.model_routing_residue_file import (
    ModelRoutingResidueFile,
)


class ModelRoutingAuthorityInput(BaseModel):
    """Pure input for ValidatorRoutingAuthority.handle.

    Every field is supplied by the runner / EFFECT boundary — the COMPUTE handler
    never touches the filesystem. Required model_routing keys, provider literals,
    fallback-endpoint env tokens, skip tokens, and CLI markers are configuration
    so the same handler validates any repo whose boundary supplies its corpus.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    repo: str = Field(description="Repo name used in finding locations and evidence.")

    # POSITIVE proof: demo-path node contracts whose model_routing must resolve
    # from authority.
    demo_path_contracts: tuple[ModelRoutingAuthorityFile, ...] = Field(
        default_factory=tuple,
        description="Demo-path node contract.yaml files (loaded text).",
    )
    required_routing_keys: tuple[str, ...] = Field(
        default_factory=lambda: (
            "provider",
            "served_model_id",
            "endpoint_ref",
            "routing_source",
        ),
        description="model_routing keys that MUST be present and contract-declared.",
    )

    # NEGATIVE audit: exact demo-path source files subjected to the AST scan.
    demo_path_sources: tuple[ModelRoutingAuthorityFile, ...] = Field(
        default_factory=tuple,
        description="Demo-path Python source files (loaded text) for the negative audit.",
    )
    provider_literal_tokens: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Provider host literals that must not be hardcoded post-routing.",
    )
    fallback_endpoint_env_tokens: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Shared endpoint env-var names a demo path must not read.",
    )
    skip_tokens: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Inline skip-token vocabulary honored by the negative audit.",
    )

    # RESIDUE audit (burn-down ratchet).
    residue_files: tuple[ModelRoutingResidueFile, ...] = Field(
        default_factory=tuple,
        description="Confirmed env-authority residue files with baselines.",
    )

    # PROVIDER-CLASS ENDPOINT SHAPE audit: the bifrost delegation config text.
    bifrost_config: ModelRoutingAuthorityFile | None = Field(
        default=None,
        description="bifrost_delegation.yaml text (loaded at the boundary), or None.",
    )
    cli_agent_tiers: tuple[str, ...] = Field(
        default_factory=lambda: ("cli_agents",),
        description="Forbidden shelled-CLI tier names (OMN-13215).",
    )

    # DELEGATION-PROFILE semantic check (folded-in validator_delegation_profile).
    delegation_profiles: tuple[ModelRoutingAuthorityFile, ...] = Field(
        default_factory=tuple,
        description="Delegation runtime profile YAML files (loaded text) to validate.",
    )


__all__ = ["ModelRoutingAuthorityInput"]
