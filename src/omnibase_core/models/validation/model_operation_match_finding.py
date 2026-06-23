# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelOperationMatchFinding — finding from the operation_match operation guard (OMN-13530)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ModelOperationMatchFinding:
    """A handler_routing entry that routes by operation but lacks an ``operation`` field.

    RuntimeLocal._validate_routing requires an ``operation`` field on every handler
    entry whose ``routing_strategy`` is not ``payload_type_match`` (i.e.
    ``operation_match``, or an absent strategy which defaults to that branch). A
    missing ``operation`` makes the contract fail closed at startup with
    ``handlers[i].operation is missing`` — the node never loads.
    """

    path: Path
    handler_index: int
    strategy: str
    handler_name: str

    def format(self) -> str:
        strategy = self.strategy or "(absent → defaults to operation_match)"
        return (
            f"{self.path}: handlers[{self.handler_index}] "
            f"(handler={self.handler_name}) is missing 'operation' "
            f"(routing_strategy={strategy})"
        )
