# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelDispatchedContractOperationFinding — dispatched-contract handlers[0].operation guard (OMN-13324)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelDispatchedContractOperationFinding:
    """A dispatched node contract whose ``handlers[0]`` lacks a non-empty ``operation``.

    The dispatch-envelope unwrap path (``node_dod_verify``
    ``test_dispatch_envelope_unwrap.py`` and the dispatch engine generally) resolves
    the primary handler's ``operation`` from ``handler_routing.handlers[0].operation``.
    A dispatched contract that omits it surfaces as ``handlers[0].operation is
    missing`` and the dispatch never resolves an operation.

    This finding is scoped to the FIRST handler of any contract that declares a
    non-empty ``handler_routing.handlers`` list — i.e. every dispatchable node
    contract. It is intentionally strategy-agnostic: unlike the operation_match
    guard (OMN-13530), which exempts ``payload_type_match``, the dispatch-unwrap
    surface reads ``handlers[0].operation`` regardless of routing_strategy.
    """

    path: Path
    handler_name: str
    routing_strategy: str

    def format(self) -> str:
        strategy = self.routing_strategy or "(absent)"
        return (
            f"{self.path}: handlers[0] (handler={self.handler_name}) is missing "
            f"a non-empty 'operation' field (routing_strategy={strategy})"
        )
