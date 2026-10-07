# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI and pre-commit runtime for the shrink-only boundary import gate.

Every tracked eligible Python file and src/<pkg> YAML value is scanned, including
entire Python strings naming node modules. Identities retain every symbol.
``--base`` defaults to HEAD; CI supplies the merge base. Candidate baseline
entries must exist at that revision. Adoption when no base baseline exists
requires ``--bootstrap``. Writes refuse growth against both current and base
state. All filesystem and Git I/O runs through canonical EFFECT handlers.
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
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
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
    parser.add_argument("--base", default="HEAD", help="base revision (CI: merge base)")
    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="adopt only when the base has no baseline",
    )
    parser.add_argument("--report-json")
    parser.add_argument("--edges-json")
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args(argv)
    effect = NodeBoundaryImportCheckEffect()
    module_pairs = 0
    adopted = False
    try:
        request = effect.handle(
            ModelBoundaryImportCheckRequest(
                root=args.root,
                baseline_path=args.baseline,
                base=args.base,
                bootstrap=args.bootstrap,
            )
        )
        edges, _ = extract_edges(request)
        module_pairs = len({(edge.importer, edge.target) for edge in edges})
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
            added = set[str]()
            if request.baseline_present:
                added.update(observed - set(request.baseline_edges))
            if request.base_baseline_present:
                added.update(observed - set(request.base_baseline_edges))
            if added:
                sys.stderr.write(
                    "Refusing baseline growth; new edges:\n"
                    + "".join(f"  {edge}\n" for edge in sorted(added))
                )
            elif (
                not request.base_baseline_present or not request.baseline_present
            ) and not request.bootstrap:
                sys.stderr.write(
                    "Refusing baseline adoption: missing current or base baseline; pass --bootstrap.\n"
                )
                report = ModelValidationReport.from_findings(
                    findings=report.findings
                    + (
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id="baseline-bootstrap-unflagged",
                            location=request.baseline_path,
                            message="Writing an absent current or base baseline requires --bootstrap.",
                        ),
                    ),
                    request=ModelValidationRequestRef(profile="default"),
                    validators_run=(VALIDATOR_ID,),
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
                request = request.model_copy(update={"baseline_present": True})
        adopted = (
            request.bootstrap
            and request.baseline_present
            and not request.base_baseline_present
            and report.overall_status == "PASS"
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
    sys.stdout.write(f"Module pairs: {module_pairs}\n")
    if adopted:
        sys.stdout.write(
            f"Baseline adoption authorized by --bootstrap: no base baseline at {args.base}.\n"
        )
    for finding in report.findings:
        sys.stdout.write(f"  {finding.location}: {finding.message}\n")
    return 0 if report.overall_status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
