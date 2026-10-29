# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Contract walker CLI, report-only (OMN-19553).

`uv run python -m omnibase_core.nodes.node_contract_walker_check_compute.runtime_contract_walker_check`

Exits 0 whatever the walker finds (report-only by the operator ruling of 2026-09-25).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.models.nodes.contract_walker_check.model_contract_walker_check_input import (
    ModelContractWalkerCheckInput,
)
from omnibase_core.models.nodes.text_file_write.model_text_file_write_input import (
    ModelTextFileWriteInput,
)
from omnibase_core.models.validation.model_contract_walk_report import (
    ModelContractWalkReport,
)
from omnibase_core.nodes.node_contract_walker_check_compute.handler import (
    NodeContractWalkerCheckCompute,
)
from omnibase_core.nodes.node_text_file_write_effect.handler import (
    NodeTextFileWriteEffect,
)
from omnibase_core.validation.validator_contract_walker import (
    DEFAULT_MAX_PRODUCT_STATES,
)


def _summary_lines(report: ModelContractWalkReport) -> list[str]:
    s = report.summary
    lines = [
        "contract walker (report-only; findings never fail this command)",
        f"  contracts scanned {s.contracts_scanned}; declaring a machine "
        f"{s.machine_contracts}; walked {s.walked_contracts}; NOT_ARMED "
        f"{s.not_armed_contracts}",
        f"  workflows {s.workflows}; selected paths {s.selected_paths} "
        f"(golden {s.golden_paths}, error {s.error_paths}, open {s.open_paths}); "
        f"cover all-edges, loop bound 1",
        f"  error edges {s.error_edges}; illegal (state, trigger) pairs "
        f"{s.illegal_pairs}",
        f"  defects: unreachable states {s.unreachable_states}; dead states "
        f"{s.dead_states}; no golden exit {s.no_golden_exit_states}; uncovered "
        f"transitions {s.uncovered_transitions}; "
        f"truncated workflows {s.truncated_workflows}",
    ]
    for workflow in report.workflows:
        nodes = "+".join(c.node for c in workflow.components)
        lines.append(
            f"  {workflow.workflow_owner}: [{nodes}] states {workflow.product_state_count}, "
            f"edges {workflow.product_edge_count}, paths {workflow.selected_path_count}, "
            f"error edges {len(workflow.error_edges)}, unreachable "
            f"{len(workflow.unreachable_states)}, dead {len(workflow.dead_states)}, "
            f"no golden exit {len(workflow.no_golden_exit_states)}, "
            f"uncovered {len(workflow.uncovered_transitions)}"
        )
    for item in report.not_armed:
        lines.append(f"  NOT_ARMED {item.node}: {item.reason}")
    return lines


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=(
            "python -m omnibase_core.nodes.node_contract_walker_check_compute"
            ".runtime_contract_walker_check"
        ),
        description=(
            "Walk contract state machines and report golden paths, error edges, "
            "illegal state/trigger pairs and defects. Report-only: exits 0 "
            "whatever it finds."
        ),
    )
    parser.add_argument(
        "roots",
        nargs="*",
        default=["src"],
        help="Directories (or contract.yaml files) to scan; default src",
    )
    parser.add_argument("--json-out", help="Write the JSON report to this path")
    parser.add_argument(
        "--max-product-states",
        type=int,
        default=DEFAULT_MAX_PRODUCT_STATES,
        help="Product-graph state cap per workflow; hitting it is reported",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    report = NodeContractWalkerCheckCompute().handle(
        ModelContractWalkerCheckInput(
            roots=tuple(Path(root) for root in args.roots),
            max_product_states=args.max_product_states,
        )
    )
    if args.json_out:
        text = report.model_dump_json(indent=2) + "\n"
        if args.json_out == "-":
            sys.stdout.write(text)
        else:
            NodeTextFileWriteEffect().handle(
                ModelTextFileWriteInput(path=args.json_out, text=text)
            )
    sys.stdout.write("\n".join(_summary_lines(report)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
