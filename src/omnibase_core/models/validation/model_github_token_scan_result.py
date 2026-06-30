# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelGithubTokenScanResult — output of github-token env-read COMPUTE handler (OMN-13310)."""

from __future__ import annotations

__all__ = ["ModelGithubTokenScanResult"]

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.validation.model_github_token_violation import (
    ModelGithubTokenViolation,
)


class ModelGithubTokenScanResult(BaseModel):
    """Output of HandlerGithubTokenEnvReads (COMPUTE result, JSON-ledger-safe).

    Returned as ``ModelHandlerOutput.result`` by the COMPUTE handler.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    violations: tuple[ModelGithubTokenViolation, ...] = Field(
        default=(),
        description="All raw GitHub-token env reads found across the scanned files",
    )
    files_scanned: int = Field(ge=0, description="Number of files examined")
    files_skipped: int = Field(
        ge=0, description="Number of files skipped (allowlisted or unreadable)"
    )

    @property
    def is_clean(self) -> bool:
        """Return True iff no violations were found."""
        return len(self.violations) == 0
