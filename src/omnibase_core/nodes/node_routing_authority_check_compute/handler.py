# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""NodeRoutingAuthorityCheckCompute — routing-authority verification COMPUTE handler.

Ported from omnimarket/scripts/ci/check_routing_authority.py (OMN-12821,
OMN-12877, OMN-12883) into a canonical COMPUTE node on ProtocolMessageHandler.
Also consolidates the previously unwired core validator_delegation_profile
(OMN-13306, W6b).

Architecture: COMPUTE node — pure, deterministic, no I/O inside the handler.
File contents arrive via the envelope payload; the I/O of loading files happens
at the EFFECT boundary (the CLI runner / pre-commit hook), never inside the
handler.

ProtocolMessageHandler implementation: structural duck-typing (matches the
protocol; not a subclass of ValidatorBase or any Plugin* base class).

The check algorithm itself lives in
``omnibase_core.validation.checker_routing_authority`` (OMN-3210 layering
burn-down / OMN-14289) — this node is a thin coordination shell over that
validation-layer logic, per the "nodes are thin, handlers own logic" repo
invariant. Importing that module here (nodes -> validation) is a
doctrine-legal direction; the reverse (a validation module importing this
node) was the frozen `validation -> nodes` back-edge OMN-14289 retired.

See: OMN-13306 (W6b), OMN-12821, OMN-12877, OMN-12883, OMN-9048, OMN-3210
"""

from __future__ import annotations

from typing import Any

from omnibase_core.models.validation.model_residue_entry import (
    ModelResidueEntry,
)
from omnibase_core.models.validation.model_routing_authority_check_input import (
    ModelRoutingAuthorityCheckInput,
)
from omnibase_core.models.validation.model_routing_authority_check_output import (
    ModelRoutingAuthorityCheckOutput,
)
from omnibase_core.models.validation.model_routing_contract_entry import (
    ModelRoutingContractEntry,
)
from omnibase_core.validation.checker_routing_authority import (
    check_routing_authority_at_path,
    resolve_endpoint_for_ref,
    run_routing_authority_check,
)

__all__ = [
    "NodeRoutingAuthorityCheckCompute",
    "ModelRoutingAuthorityCheckInput",
    "ModelRoutingAuthorityCheckOutput",
    "ModelResidueEntry",
    "ModelRoutingContractEntry",
    "check_routing_authority_at_path",
]


class NodeRoutingAuthorityCheckCompute:
    """Routing-authority verification COMPUTE handler.

    Pure, deterministic, no filesystem/network I/O inside the handler.
    All file contents arrive via the ``ModelRoutingAuthorityCheckInput`` payload.

    Satisfies ProtocolMessageHandler structurally (duck-typing). Register via
    DI container or invoke directly in tests.

    The ``check()`` method is the synchronous computation entry-point used by
    the pre-commit CLI wrapper. The ``handle()`` method wraps it for dispatch-
    engine consumption (async envelope in, async envelope out). Both delegate
    to the pure validation-layer implementation in
    ``omnibase_core.validation.checker_routing_authority``.
    """

    @property
    def handler_id(self) -> str:
        return "routing-authority-check-compute"

    @property
    def message_types(self) -> set[str]:
        return {"RoutingAuthorityCheckRequested"}

    @property
    def node_kind(self) -> Any:
        from omnibase_core.enums.enum_node_kind import EnumNodeKind

        return EnumNodeKind.COMPUTE

    @property
    def category(self) -> Any:
        from omnibase_core.enums.enum_execution_shape import (
            EnumMessageCategory,
        )

        return EnumMessageCategory.COMMAND

    # ------------------------------------------------------------------
    # Core computation (synchronous — pure function over payload data)
    # ------------------------------------------------------------------

    def check(
        self, inp: ModelRoutingAuthorityCheckInput
    ) -> ModelRoutingAuthorityCheckOutput:
        """Run all four audits and return a structured verdict.

        Pure: all inputs arrive through ``inp``; no filesystem reads.
        """
        return run_routing_authority_check(inp)

    async def handle(self, envelope: Any) -> Any:
        """Dispatch-engine entry-point — wraps check() for async bus invocation."""

        from omnibase_core.models.dispatch.model_handler_output import (
            ModelHandlerOutput,
        )

        inp: ModelRoutingAuthorityCheckInput = envelope.payload
        result = self.check(inp)
        return ModelHandlerOutput.for_compute(
            input_envelope_id=envelope.envelope_id,
            correlation_id=envelope.correlation_id,
            handler_id=self.handler_id,
            result=result,
        )

    def _resolve_endpoint_for_ref(
        self,
        endpoint_ref: str,
        bifrost_content: str,
        bifrost_rel: str,
    ) -> tuple[str | None, str | None, str]:
        return resolve_endpoint_for_ref(endpoint_ref, bifrost_content, bifrost_rel)
