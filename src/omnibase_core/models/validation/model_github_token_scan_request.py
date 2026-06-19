# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGithubTokenScanRequest — input payload for github-token env-read COMPUTE handler (OMN-13310)."""

from __future__ import annotations

__all__ = ["ModelGithubTokenScanRequest"]

from pydantic import BaseModel, ConfigDict, Field


class ModelGithubTokenScanRequest(BaseModel):
    """Input payload for HandlerGithubTokenEnvReads.

    ``files`` maps relative-or-absolute path strings to their UTF-8 source
    text.  All I/O must be performed by the EFFECT boundary before passing
    this payload; the COMPUTE handler never reads the filesystem.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    files: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of file path -> source text to scan",
    )
