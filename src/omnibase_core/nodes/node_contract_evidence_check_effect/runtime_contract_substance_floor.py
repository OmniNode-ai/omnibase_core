# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the contract substance floor check (OMN-14409)."""

from __future__ import annotations

import sys
from pathlib import Path

from omnibase_core.models.nodes.contract_evidence_check.model_contract_substance_floor_request import (
    ModelContractSubstanceFloorRequest,
)
from omnibase_core.nodes.node_contract_evidence_check_effect.handler_contract_substance_floor import (
    HandlerContractSubstanceFloor,
)

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Check each contract file named on the command line against the floor.

    The OCC copy also swept the whole ``contracts/`` corpus and read a legacy
    allowlist (OMN-14419); core carries neither, so every named contract that
    fails the floor fails the run.
    """
    paths = [Path(arg) for arg in (sys.argv[1:] if argv is None else argv)]
    if not paths:
        sys.stderr.write(
            "usage: python -m omnibase_core.nodes.node_contract_evidence_check_effect."
            "runtime_contract_substance_floor <contract.yaml> [...]\n"
        )
        return 2
    report = HandlerContractSubstanceFloor().handle(
        ModelContractSubstanceFloorRequest(paths=tuple(paths))
    )
    failures = [verdict for verdict in report.verdicts if not verdict.passed]
    for verdict in failures:
        sys.stderr.write(f"  {verdict.failure_message}\n\n")
    if failures:
        sys.stderr.write(
            f"{len(failures)} contract(s) failed the substance floor (OMN-14409)\n"
        )
        return 1
    sys.stdout.write(f"substance floor OK: {len(paths)} contract(s) checked\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
