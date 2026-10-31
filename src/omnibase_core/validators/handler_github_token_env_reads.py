# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerGithubTokenEnvReads — COMPUTE handler for github-token env-read ban (OMN-13310).

A COMPUTE handler whose ``handle(request)`` takes ``ModelGithubTokenScanRequest``
and returns ``ModelGithubTokenScanResult``; the event envelope belongs to the shared
runtime, not to this handler.

The handler is **pure**: it never reads the filesystem.  File bytes are supplied
via ``ModelGithubTokenScanRequest.files``; violations are returned in the
JSON-ledger-safe result model.
"""

from __future__ import annotations

__all__ = ["HandlerGithubTokenEnvReads"]

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.validation.model_github_token_scan_request import (
    ModelGithubTokenScanRequest,
)
from omnibase_core.models.validation.model_github_token_scan_result import (
    ModelGithubTokenScanResult,
)
from omnibase_core.validation.validator_github_token_env_reads import (
    _is_allowlisted,
    scan_source,
)


class HandlerGithubTokenEnvReads:
    """COMPUTE handler: scan file source texts for raw GitHub-token env reads.

    Request: ``ModelGithubTokenScanRequest``
    Result:  ``ModelGithubTokenScanResult``

    The handler is **pure**: it never reads the filesystem.  File bytes are
    supplied via ``ModelGithubTokenScanRequest.files``; violations are returned
    in the JSON-ledger-safe result model.
    """

    @property
    def handler_id(self) -> str:
        return "github-token-env-reads-compute"

    @property
    def category(self) -> EnumMessageCategory:
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"GithubTokenScanCommand"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    async def handle(
        self,
        request: ModelGithubTokenScanRequest,
    ) -> ModelGithubTokenScanResult:
        """Scan files supplied in the request for GitHub-token env reads.

        Args:
            request: The ``ModelGithubTokenScanRequest`` naming the file texts.

        Returns:
            ``ModelGithubTokenScanResult`` with the violations and file counts.
        """
        from omnibase_core.models.validation.model_github_token_violation import (
            ModelGithubTokenViolation,
        )

        all_violations: list[ModelGithubTokenViolation] = []
        files_scanned = 0
        files_skipped = 0

        for file_path, source in request.files.items():
            rel = file_path.replace("\\", "/")
            if _is_allowlisted(rel):
                files_skipped += 1
                continue
            files_scanned += 1
            all_violations.extend(scan_source(source, file_path=file_path))

        return ModelGithubTokenScanResult(
            violations=tuple(all_violations),
            files_scanned=files_scanned,
            files_skipped=files_skipped,
        )
