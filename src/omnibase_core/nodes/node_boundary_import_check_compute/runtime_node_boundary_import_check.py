# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI and pre-commit runtime for the shrink-only boundary import gate.

No filenames are accepted: every git-tracked eligible Python file is scanned.
Missing state is an empty baseline. ``--write-baseline`` bootstraps absent state
or removes retired edges; growth of existing state is always refused. All
filesystem and Git I/O runs through canonical EFFECT handlers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import PurePath

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_artifact_write_input import (
    ModelBoundaryImportArtifactWriteInput,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_check_request import (
    ModelBoundaryImportCheckRequest,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_boundary_import_check_compute.analyzer import (
    DEFAULT_BASELINE,
    VALIDATOR_ID,
    extract_edges,
    render_baseline,
)
from omnibase_core.nodes.node_boundary_import_check_compute.handler import (
    NodeBoundaryImportCheckCompute,
)
from omnibase_core.nodes.node_boundary_import_check_effect.handler import (
    NodeBoundaryImportCheckEffect,
)


def main(argv: list[str] | None = None) -> int:
    """Return 0 for PASS or a safe baseline write, and 1 for FAIL/ERROR."""
    parser = argparse.ArgumentParser(
        description="Node-boundary import gate (OMN-17427)"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--report-json")
    parser.add_argument("--edges-json")
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)
    effect = NodeBoundaryImportCheckEffect()
    try:
        request = effect.handle(
            ModelBoundaryImportCheckRequest(root=args.root, baseline_path=args.baseline)
        )
        edges, _ = extract_edges(request)
        report = NodeBoundaryImportCheckCompute().handle(request)
        if args.edges_json:
            effect.write_artifact(
                ModelBoundaryImportArtifactWriteInput(
                    path=args.edges_json,
                    content=json.dumps(
                        [edge.model_dump(mode="json") for edge in edges], indent=2
                    )
                    + "\n",
                )
            )
        if args.write_baseline and report.overall_status != "ERROR":
            observed = {edge.identity for edge in edges}
            added = observed - set(request.baseline_edges)
            if request.baseline_present and added:
                sys.stderr.write(
                    "Refusing baseline growth; new edges:\n"
                    + "".join(f"  {edge}\n" for edge in sorted(added))
                )
            else:
                effect.write_artifact(
                    ModelBoundaryImportArtifactWriteInput(
                        path=str(PurePath(args.root) / args.baseline),
                        content=render_baseline(tuple(sorted(observed))),
                    )
                )
                report = NodeBoundaryImportCheckCompute().handle(
                    request.model_copy(
                        update={
                            "baseline_edges": tuple(sorted(observed)),
                            "baseline_present": True,
                        }
                    )
                )
        if args.report_json:
            effect.write_report(args.report_json, report)
    except (OSError, ModelOnexError, ValueError) as exc:
        report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (str(exc),))
        if args.report_json:
            try:
                effect.write_report(args.report_json, report)
            except (OSError, ModelOnexError) as write_error:
                sys.stderr.write(f"ERROR writing report: {write_error}\n")
    sys.stdout.write(f"{report.overall_status}: {report.metrics.total} findings\n")
    for finding in report.findings:
        sys.stdout.write(f"  {finding.location}: {finding.message}\n")
    return 0 if report.overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
