# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract data for the Slice A ratchets."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.finding_baseline.model_legacy_ratchet_rule import (
    ModelLegacyRatchetRule,
)


class ModelLegacyRatchetRules(BaseModel):
    """Adapter bindings loaded by the existing finding-baseline effect runtime."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rules: tuple[ModelLegacyRatchetRule, ...]
    default_dirs: tuple[str, ...]
    pyright_project: str
