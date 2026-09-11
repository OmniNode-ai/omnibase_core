# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Immutable package-only deploy binding and its canonical manifest digest."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.ticket.model_package_only_manifest_entry import (
    ModelPackageOnlyManifestEntry,
)

_GIT_SHA_PATTERN = r"^[0-9a-f]{40}$"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
_SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
_MAX_POLICY_ID_LENGTH = 100


def compute_package_only_manifest_sha256(
    entries: tuple[ModelPackageOnlyManifestEntry, ...],
) -> str:
    """Return the deterministic SHA-256 digest for a typed manifest entry set."""
    serialized_entries = [entry.model_dump(mode="json") for entry in entries]
    serialized_entries.sort(
        key=lambda entry: json.dumps(
            entry,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    canonical = json.dumps(
        serialized_entries,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


class ModelPackageOnlyDeployBinding(BaseModel):
    """Immutable source identity and complete diff manifest for deploy-gate input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    repository: Literal["OmniNode-ai/omnibase_core"] = Field(
        ...,
        description="Canonical Core repository authorized by this binding model.",
    )
    base_sha: str = Field(
        ...,
        pattern=_GIT_SHA_PATTERN,
        description="Exact 40-character Git base commit.",
    )
    head_sha: str = Field(
        ...,
        pattern=_GIT_SHA_PATTERN,
        description="Exact 40-character Git head commit.",
    )
    diff_base_sha: str = Field(
        ...,
        pattern=_GIT_SHA_PATTERN,
        description=(
            "Exact merge-base commit used by GitHub to calculate changed_files."
        ),
    )
    # string-id-ok: stable package-only policy identifier, not a system UUID
    policy_id: str = Field(
        ...,
        min_length=1,
        max_length=_MAX_POLICY_ID_LENGTH,
        description="Stable identifier of the policy evaluated by the handler.",
    )
    policy_version: str = Field(
        ...,
        pattern=_SEMVER_PATTERN,
        description="SemVer version of the evaluated policy.",
    )
    manifest_sha256: str = Field(
        ...,
        pattern=_SHA256_PATTERN,
        description="Canonical SHA-256 digest of the complete changed_files manifest.",
    )
    changed_files: tuple[ModelPackageOnlyManifestEntry, ...] = Field(
        ...,
        min_length=1,
        description="Complete typed changed-file manifest.",
    )

    @model_validator(mode="after")
    def validate_manifest_identity(self) -> ModelPackageOnlyDeployBinding:
        """Reject ambiguous commit identities, duplicate paths, and stale digests."""
        if self.base_sha == self.head_sha:
            msg = "base_sha and head_sha must identify different commits"
            raise ValueError(msg)
        if self.diff_base_sha == self.head_sha:
            msg = "diff_base_sha and head_sha must identify different commits"
            raise ValueError(msg)
        filenames = [entry.filename for entry in self.changed_files]
        if len(filenames) != len(set(filenames)):
            msg = "changed_files must not contain duplicate filenames"
            raise ValueError(msg)
        expected_digest = compute_package_only_manifest_sha256(self.changed_files)
        if self.manifest_sha256 != expected_digest:
            msg = "manifest_sha256 does not match the canonical changed_files digest"
            raise ValueError(msg)
        return self


__all__ = [
    "ModelPackageOnlyDeployBinding",
    "compute_package_only_manifest_sha256",
]
