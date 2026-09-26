# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
VersionStatus model for node introspection.
"""

from pydantic import BaseModel, ConfigDict


class ModelVersionStatus(BaseModel):
    """Model for version status information."""

    model_config = ConfigDict(extra="forbid")

    latest: str | None = None
    supported: list[str] | None = None
    deprecated: list[str] | None = None
    # Add more fields as needed for protocol
