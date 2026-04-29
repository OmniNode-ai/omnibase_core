# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from enum import StrEnum


class EnumArtifactStoreAction(StrEnum):
    """Actions the overseer can request from an artifact store provider.

    Used in protocol dispatch to blob/artifact storage integrations
    (e.g. S3, GCS, local fs).
    """

    UPLOAD = "UPLOAD"
    """Upload an artifact to the store."""

    DOWNLOAD = "DOWNLOAD"
    """Download an artifact from the store."""

    DELETE = "DELETE"
    """Delete an artifact from the store."""

    LIST = "LIST"
    """List artifacts at a given prefix or path."""

    EXISTS = "EXISTS"
    """Check whether an artifact exists at a given key."""

    GET_METADATA = "GET_METADATA"
    """Retrieve metadata for an artifact without downloading its content."""

    COPY = "COPY"
    """Copy an artifact to a new key within the store."""

    MOVE = "MOVE"
    """Move an artifact to a new key (copy + delete source)."""


__all__: list[str] = ["EnumArtifactStoreAction"]
