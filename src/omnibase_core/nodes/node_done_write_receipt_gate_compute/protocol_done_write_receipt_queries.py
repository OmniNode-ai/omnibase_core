# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Public verdict-reading operations of the Done-write receipt gate handler module."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolDoneWriteReceiptQueries(Protocol):
    """Read verdicts and criteria through the contract handler's public functions."""

    def has_verified_bound_check(self, verdict: dict[str, object]) -> bool:
        """Delegate to the exported has_verified_bound_check function."""
        ...

    def as_int(self, value: object) -> int:
        """Delegate to the exported as_int function."""
        ...

    def extract_dod_verify_verdict(
        self, receipt: dict[str, object]
    ) -> tuple[dict[str, object] | None, str]:
        """Delegate to the exported extract_dod_verify_verdict function."""
        ...

    def live_acceptance_criteria_items(self, description: str) -> list[str]:
        """Delegate to the exported live_acceptance_criteria_items function."""
        ...

    def canonical_ac_label(self, text: str) -> str:
        """Delegate to the exported canonical_ac_label function."""
        ...

    def criterion_is_state_shaped(self, criterion: str) -> bool:
        """Delegate to the exported criterion_is_state_shaped function."""
        ...

    def check_records(
        self, verdict: dict[str, object]
    ) -> tuple[dict[str, object], ...]:
        """Delegate to the exported check_records function."""
        ...

    def check_status(self, check: dict[str, object]) -> str:
        """Delegate to the exported check_status function."""
        ...


__all__ = ["ProtocolDoneWriteReceiptQueries"]
