# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerGithubTokenEnvReads — COMPUTE handler for github-token env-read ban (OMN-13310).

Implements ``ProtocolMessageHandler`` as a COMPUTE node.  Input payload:
``ModelGithubTokenScanRequest``; result type: ``ModelGithubTokenScanResult``.

The handler is **pure**: it never reads the filesystem.  File bytes are supplied
via ``ModelGithubTokenScanRequest.files``; violations are returned as
``ModelHandlerOutput.result`` (JSON-ledger-safe Pydantic model).

COMPUTE constraints enforced by ``ModelHandlerOutput.for_compute``:
- no events[], no intents[], no projections[]
- result is required and must be JSON-ledger-safe
"""

from __future__ import annotations

__all__ = ["HandlerGithubTokenEnvReads"]

from uuid import UUID, uuid4

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
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

    Implements ``ProtocolMessageHandler`` (structural) as a COMPUTE node.
    Input payload: ``ModelGithubTokenScanRequest``
    Result type:   ``ModelGithubTokenScanResult``

    The handler is **pure**: it never reads the filesystem.  File bytes are
    supplied via ``ModelGithubTokenScanRequest.files``; violations are returned
    as ``ModelHandlerOutput.result`` (JSON-ledger-safe Pydantic model).
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
        envelope: ModelEventEnvelope[ModelGithubTokenScanRequest],
    ) -> ModelHandlerOutput[ModelGithubTokenScanResult]:
        """Scan files supplied in the envelope payload for GitHub-token env reads.

        Args:
            envelope: Input envelope with ``ModelGithubTokenScanRequest`` payload.

        Returns:
            ``ModelHandlerOutput[ModelGithubTokenScanResult]`` with ``result`` set.
        """
        from omnibase_core.models.validation.model_github_token_violation import (
            ModelGithubTokenViolation,
        )

        request = envelope.payload
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

        result = ModelGithubTokenScanResult(
            violations=tuple(all_violations),
            files_scanned=files_scanned,
            files_skipped=files_skipped,
        )

        correlation_id: UUID = envelope.correlation_id or uuid4()

        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=correlation_id,
            handler_id=self.handler_id,
            result=result,
        )
