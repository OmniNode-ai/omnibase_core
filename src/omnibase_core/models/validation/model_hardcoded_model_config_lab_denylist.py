# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The operator's private vocabulary of the hardcoded model-configuration guard."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from omnibase_core.models.validation.model_hardcoded_model_config_tier_engine_vocabulary import (
    ModelHardcodedModelConfigTierEngineVocabulary,
)


class ModelHardcodedModelConfigLabDenylist(
    ModelHardcodedModelConfigTierEngineVocabulary
):
    """The operator's private list of dead endpoints (OMN-20939), lab
    deployment facts (OMN-21147) and further tier and engine names (OMN-21463).

    Lives outside this repository, in the workspace config root's vocabularies,
    and is added to the policy's lists of the same names when present.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    schema_version: int = Field(ge=1, description="Vocabulary schema version")
    retired_values: tuple[str, ...] = Field(
        min_length=1, description="Exact retired endpoint strings (family R)"
    )
    lab_host_names: tuple[str, ...] = Field(
        default=(), description="Lab host names (family D)"
    )
    lab_ports: tuple[int, ...] = Field(default=(), description="Lab ports (family D)")
