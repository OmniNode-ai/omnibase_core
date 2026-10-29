# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerBackendSecretDisciplineCompute — the node's thin COMPUTE handler (OMN-13305).

The scanners and the verdict builder are pure and live in
``omnibase_core.validation.validator_backend_secret_discipline``; this handler
wraps them behind the canonical typed request / response interface.
"""

from __future__ import annotations

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.validation.model_backend_secret_discipline_input import (
    ModelBackendSecretDisciplineInput,
)
from omnibase_core.models.validation.model_backend_secret_discipline_output import (
    ModelBackendSecretDisciplineOutput,
)
from omnibase_core.validation.validator_backend_secret_discipline import (
    build_report_from_files,
)

__all__ = ["HandlerBackendSecretDisciplineCompute"]


class HandlerBackendSecretDisciplineCompute:
    """Backend-secret-discipline validator as a canonical COMPUTE handler.

    Implements ``ProtocolMessageHandler`` (structural protocol, not base-class
    inheritance). The handler is pure and deterministic: all file-loading I/O
    happens at the EFFECT boundary (CLI / runner); the handler receives only
    pre-loaded content via the envelope payload.

    Node archetype: COMPUTE (pure, idempotent, no side effects).
    """

    # --- ProtocolMessageHandler protocol ---

    @property
    def handler_id(self) -> str:
        return "node.backend-secret-discipline.compute"

    @property
    def category(self) -> EnumMessageCategory:
        return EnumMessageCategory.COMMAND

    @property
    def message_types(self) -> set[str]:
        return {"BackendSecretDisciplineCheck"}

    @property
    def node_kind(self) -> EnumNodeKind:
        return EnumNodeKind.COMPUTE

    def handle(
        self, request: ModelBackendSecretDisciplineInput
    ) -> ModelBackendSecretDisciplineOutput:
        """Run the backend-secret-discipline check and return a typed verdict.

        Definition-B canonical shape (OMN-14355): typed request in, typed
        response out, no envelope reference in the core. The shared runtime
        adapter (``omnibase_core.runtime.runtime_local_adapter``) owns the
        envelope boundary and adapts this call from the bus message.

        ``request`` supplies all file contents to scan; the handler performs
        no filesystem I/O.

        Args:
            request: ``ModelBackendSecretDisciplineInput`` payload.

        Returns:
            ``ModelBackendSecretDisciplineOutput`` verdict.
        """
        return build_report_from_files(request.config_contents)
