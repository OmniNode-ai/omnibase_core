# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""NodeGithubTokenEnvReadsCheckCompute — raw GitHub-token env-read COMPUTE handler.

Pure and deterministic: file source text arrives on the request; reading files
and printing happen in the runtime, never here. The scanner lives in
``omnibase_core.validation.validator_github_token_env_reads``.

Ticket: OMN-21520 (fleet gate: OMN-13310, OMN-12856).
"""

from __future__ import annotations

from omnibase_core.models.validation.model_github_token_scan_request import (
    ModelGithubTokenScanRequest,
)
from omnibase_core.models.validation.model_github_token_scan_result import (
    ModelGithubTokenScanResult,
)
from omnibase_core.models.validation.model_github_token_violation import (
    ModelGithubTokenViolation,
)
from omnibase_core.validation.validator_github_token_env_reads import (
    _is_allowlisted,
    scan_source,
)

__all__ = ["NodeGithubTokenEnvReadsCheckCompute"]


class NodeGithubTokenEnvReadsCheckCompute:
    """COMPUTE handler that scans file sources for raw GitHub-token env reads."""

    def handle(
        self, request: ModelGithubTokenScanRequest
    ) -> ModelGithubTokenScanResult:
        """Scan the supplied sources; allowlisted paths are counted as skipped."""
        violations: list[ModelGithubTokenViolation] = []
        files_scanned = 0
        files_skipped = 0
        for file_path, source in request.files.items():
            if _is_allowlisted(file_path.replace("\\", "/")):
                files_skipped += 1
                continue
            files_scanned += 1
            violations.extend(scan_source(source, file_path=file_path))
        return ModelGithubTokenScanResult(
            violations=tuple(violations),
            files_scanned=files_scanned,
            files_skipped=files_skipped,
        )
