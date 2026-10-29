# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The ledger test-write guard's refusal (OMN-19513)."""

from __future__ import annotations

from typing import Final

__all__ = ["GUARD_NAME", "ModelLedgerTestWriteRefusedError"]

GUARD_NAME: Final = "ledger-test-write-guard"


class ModelLedgerTestWriteRefusedError(Exception):
    """A test process tried to write a canonical ledger target. The message names the guard."""

    def __init__(self, signal: str, target_kind: str, target: str) -> None:
        self.signal = signal
        self.target_kind = target_kind
        self.target = target
        super().__init__(
            f"{GUARD_NAME} REFUSED -- a test process ({signal}) tried to write the canonical "
            f"{target_kind} {target}. Nothing was written. A test writes a tmp_path ledger, a "
            "non-canonical topic or a loopback DSN "
            "(omnibase_core.handlers.handler_ledger_write_guard, OMN-19513)."
        )
