# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The substance floor verdict of one contract (OMN-14409)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from omnibase_core.nodes.node_contract_evidence_check_effect.substance_floor_finding import (
    SUBSTANCE_FLOOR,
    CheckFinding,
)

__all__ = ["ContractResult"]


@dataclass
class ContractResult:
    """Substance-floor verdict for a single contract."""

    path: Path
    ticket_id: str
    findings: list[CheckFinding] = field(default_factory=list)

    @property
    def has_checks(self) -> bool:
        return bool(self.findings)

    @property
    def substantive(self) -> list[CheckFinding]:
        return [f for f in self.findings if f.is_substantive]

    @property
    def passed(self) -> bool:
        # A contract with no dod_evidence checks is out of scope for this gate
        # (the Receipt Gate governs whether a contract is required at all).
        if not self.has_checks:
            return True
        return bool(self.substantive)

    def failure_message(self) -> str:
        probes = "\n".join(
            f"      - [{f.tier.value}] {f.dod_item}: {f.check_value[:100]}"
            for f in self.findings
        )
        return (
            f"{self.path}: SUBSTANCE FLOOR FAILED — {self.ticket_id} declares "
            f"{len(self.findings)} dod_evidence check(s), and every one of them is "
            f"an existence probe (tier L0). An existence probe proves the PR object "
            f"exists; it passes identically whether the code is correct or broken.\n"
            f"    Declared checks:\n{probes}\n"
            f"    Fix: add at least one check at tier {SUBSTANCE_FLOOR.value}+ that "
            f"could fail if the work were wrong (a test, a behavioral assertion, a "
            f"guard/gate outcome, or a runtime readback). Existence/binding probes "
            f"stay valid for Evidence-Source stamping — they just cannot stand in "
            f"for proof of correctness."
        )
