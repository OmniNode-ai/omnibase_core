# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""One evidence schema with its source snapshot and hash, frozen into a manifest (OMN-22001)."""

from pydantic import BaseModel, ConfigDict, Field


class ModelManifestEvidenceSource(BaseModel):
    """Which evidence schema a manifest reads, from which snapshot, with which hash.

    Attributes:
        schema_ref: Reference to the evidence schema.
        snapshot_ref: Reference to the source snapshot.
        content_hash: SHA-256 of the snapshot content (64 lowercase hex).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_ref: str = Field(min_length=1)
    snapshot_ref: str = Field(min_length=1)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
