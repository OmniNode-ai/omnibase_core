# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input model for the routing-authority check node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_residue_entry import (
    ModelResidueEntry,
)
from omnibase_core.models.validation.model_routing_contract_entry import (
    ModelRoutingContractEntry,
)


class ModelRoutingAuthorityCheckInput(BaseModel):
    """Input payload for the routing-authority check COMPUTE handler."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    demo_path_contracts: tuple[ModelRoutingContractEntry, ...]
    """Contract files to verify model_routing from authority."""

    contract_contents: dict[str, str]
    """Mapping of contract_rel to raw YAML text."""

    bifrost_config_rel: str = "src/omnimarket/configs/bifrost_delegation.yaml"
    bifrost_config_content: str = ""
    """Raw YAML text of bifrost_delegation.yaml; empty disables the audit."""

    demo_path_sources: tuple[str, ...]
    """Source files subjected to the negative audit."""

    source_contents: dict[str, str]
    """Mapping of source_rel to raw Python source text."""

    residue_entries: tuple[ModelResidueEntry, ...]
    """Residue files with baselined violation counts."""

    residue_contents: dict[str, str]
    """Mapping of residue_rel to raw Python source text."""

    yaml_policy_residue: tuple[ModelResidueEntry, ...] = ()
    yaml_policy_contents: dict[str, str] = Field(default_factory=dict)

    skip_tokens: tuple[str, ...] = (
        "ONEX_FLAG_EXEMPT",
        "ONEX_EXCLUDE",
        "contract-config-ok",
    )

    provider_literal_tokens: tuple[str, ...] = (
        "generativelanguage.googleapis.com",
        "openrouter.ai",
        "api.openai.com",
        "api.anthropic.com",
    )

    fallback_endpoint_env_tokens: tuple[str, ...] = (
        "LLM_CODER_URL",
        "LLM_REASONER_URL",
        "LLM_BASE_URL",
        "OPENROUTER_BASE_URL",
        "endpoint_url_env",
    )

    api_key_ref_hints: tuple[str, ...] = ("api_key", "api-key", "_KEY", "_TOKEN")
    cli_url_prefix: str = "cli://"
    cli_agent_tiers: frozenset[str] = frozenset({"cli_agents"})
