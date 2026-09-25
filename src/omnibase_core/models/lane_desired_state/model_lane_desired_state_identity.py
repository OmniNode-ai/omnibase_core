# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from omnibase_core.models.lane_desired_state.model_imperative_override import (
    ModelImperativeOverride,
)
from omnibase_core.models.lane_desired_state.model_migration_bundle_id import (
    ModelMigrationBundleId,
)
from omnibase_core.models.lane_desired_state.model_resolved_image import (
    ModelResolvedImage,
)
from omnibase_core.models.lane_desired_state.model_secrets_sync_identity import (
    ModelSecretsSyncIdentity,
)
from omnibase_core.models.lane_desired_state.model_unresolved_field import (
    ModelUnresolvedField,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelLaneDesiredStateIdentity(BaseModel):
    """Whole-plane identity of a lane's desired state."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    lane_id: str = Field(  # string-id-ok: human-readable lane name, not a UUID
        ...,
        min_length=1,
        description="Unique identifier for the lane.",
    )
    lane_class: Literal["golden", "fork"] = Field(
        ...,
        description="Classification of the lane.",
    )
    source_git_sha: str | ModelUnresolvedField = Field(
        ...,
        description="Git SHA of the source or unresolved marker.",
    )
    rendered_manifest_hash: str | ModelUnresolvedField = Field(
        ...,
        description="Hash of the rendered manifest or unresolved marker.",
    )
    resolved_images: dict[str, ModelResolvedImage] | ModelUnresolvedField = Field(
        ...,
        description="Mapping of resolved images or unresolved marker.",
    )
    migration_bundle_ids: list[ModelMigrationBundleId] | ModelUnresolvedField = Field(
        ...,
        description="List of migration bundle IDs or unresolved marker.",
    )
    overlay_schema_version: ModelSemVer | ModelUnresolvedField = Field(
        ...,
        description="Version of the overlay schema or unresolved marker.",
    )
    config_schema_version: ModelSemVer | ModelUnresolvedField = Field(
        ...,
        description="Version of the config schema or unresolved marker.",
    )
    secrets_sync_identity: ModelSecretsSyncIdentity | ModelUnresolvedField = Field(
        ...,
        description="Identity of secrets sync or unresolved marker.",
    )
    imperative_overrides: list[ModelImperativeOverride] = Field(
        ...,
        description="List of imperative overrides.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def identity_hash(self) -> str:
        """Deterministic SHA-256 hash of the model state."""
        payload = self.model_dump(mode="json", exclude={"identity_hash"})
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(serialized.encode()).hexdigest()


__all__ = ["ModelLaneDesiredStateIdentity"]
