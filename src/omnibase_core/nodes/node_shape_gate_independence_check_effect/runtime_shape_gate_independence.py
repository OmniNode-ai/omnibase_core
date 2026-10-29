# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the shape-gate independence guard (OMN-20298).

Usage::

    python -m omnibase_core.nodes.node_shape_gate_independence_check_effect.runtime_shape_gate_independence [workflow.yml ...]

With no paths, every file under ``.github/workflows`` is scanned.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.validation.model_shape_gate_independence_request import (
    ModelShapeGateIndependenceRequest,
)
from omnibase_core.nodes.node_shape_gate_independence_check_effect.handler_shape_gate_independence import (
    HandlerShapeGateIndependence,
)

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refuse shape-gate detector jobs that depend on the OCC preflight."
    )
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    findings = (
        HandlerShapeGateIndependence()
        .handle(ModelShapeGateIndependenceRequest(paths=tuple(args.paths)))
        .findings
    )
    for finding in findings:
        sys.stderr.write(f"{finding.format()}\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
