# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelOverlayResolutionManifest(BaseModel):
    """Evidence artifact recording overlay resolution at runtime boot.

    stable_identity_hash() excludes timestamp and runtime_version — deterministic
    across boots with identical overlay + contract inputs.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    overlay_file_hash: str = Field(...)
    overlay_version: ModelSemVer = Field(...)
    overlay_scope_stack: tuple[str, ...] = Field(...)
    contract_requirements_hash: str = Field(
        ..., description="Hash of required keys + transport types + contract paths."
    )
    resolved_config_hash: str = Field(...)
    resolved_transports: tuple[str, ...] = Field(
        ..., description="Transports that contributed at least one resolved key."
    )
    required_transports: tuple[str, ...] = Field(
        ..., description="All transports required by contracts."
    )
    runtime_version: str = Field(...)
    timestamp: datetime = Field(...)
    config_source: str = Field(
        ..., description="overlay | legacy_env | infisical | mixed"
    )

    @field_validator("overlay_version", mode="before")
    @classmethod
    def _coerce_overlay_version(cls, v: Any) -> Any:
        if isinstance(v, str):
            return ModelSemVer.parse(v)
        return v

    def stable_identity_hash(self) -> str:
        stable = {
            "overlay_file_hash": self.overlay_file_hash,
            "contract_requirements_hash": self.contract_requirements_hash,
            "resolved_config_hash": self.resolved_config_hash,
            "resolved_transports": sorted(self.resolved_transports),
        }
        canonical = json.dumps(stable, sort_keys=True)
        return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


__all__ = ["ModelOverlayResolutionManifest"]
