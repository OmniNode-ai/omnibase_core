# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure symbol boundary ratchet against candidate and Git base baseline state."""

from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_baseline import (
    ModelBoundaryImportBaseline,
)
from omnibase_core.models.nodes.node_boundary_import_check.model_boundary_import_check_input import (
    ModelBoundaryImportCheckInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_boundary_import_check_compute.analyzer import (
    VALIDATOR_ID,
    eligible_importer,
    extract_edges,
)


class NodeBoundaryImportCheckCompute:
    """Reject new symbols, stale entries and baseline growth without I/O."""

    def handle(self, request: ModelBoundaryImportCheckInput) -> ModelValidationReport:
        """Emit canonical FAIL/ERROR findings via the shared precedence engine."""
        edges, parse_errors = extract_edges(request)
        findings = list(parse_errors)
        errors = list(request.read_errors)
        if not any(
            eligible_importer(file.path, request.repo_packages)
            for file in request.files
        ):
            errors.append("zero files scanned: an empty scan is ERROR")
        for error in errors:
            findings.append(
                ModelValidationFindingEmbed(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="scan-error",
                    message=error,
                )
            )
        baseline_error = request.baseline_error or request.base_baseline_error
        if baseline_error is None:
            try:
                ModelBoundaryImportBaseline(
                    schema_version=2,
                    gate="OMN-17427",
                    edges=list(request.baseline_edges),
                )
                ModelBoundaryImportBaseline(
                    schema_version=2,
                    gate="OMN-17427",
                    edges=list(request.base_baseline_edges),
                )
            except ValueError as exc:
                baseline_error = str(exc)
        if baseline_error is not None:
            findings.append(
                ModelValidationFindingEmbed(
                    validator_id=VALIDATOR_ID,
                    severity="ERROR",
                    rule_id="malformed-baseline",
                    location=request.baseline_path,
                    message=f"{request.baseline_path}: malformed baseline: {baseline_error}",
                )
            )
        else:
            observed = {edge.identity for edge in edges}
            baseline = set(request.baseline_edges)
            if request.base_baseline_present:
                for identity in sorted(baseline - set(request.base_baseline_edges)):
                    findings.append(
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id="baseline-growth",
                            location=request.baseline_path,
                            message=f"{identity}: new since {request.base}; the baseline only shrinks.",
                        )
                    )
            elif (request.baseline_present or baseline) and not request.bootstrap:
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        rule_id="baseline-bootstrap-unflagged",
                        location=request.baseline_path,
                        message=f"No base baseline at {request.base}; adoption requires --bootstrap.",
                    )
                )
            for edge in edges:
                if edge.identity not in baseline:
                    findings.append(
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id="new-boundary-edge",
                            location=f"{edge.importer_path}:{edge.line}",
                            message=(
                                f"{edge.identity} ({edge.kind}, seam {edge.seam}): move the shared model "
                                "to core/compat, put the protocol in spi/core "
                                "(docs/architecture/layering-exceptions.yaml in omni_home decides), "
                                "or invoke the other node through its contract on the bus; never widen the baseline."
                            ),
                        )
                    )
            for identity in sorted(baseline - observed):
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        rule_id="stale-baseline-entry",
                        location=request.baseline_path,
                        message=f"{identity}: no longer observed; remove this stale baseline entry in the same change.",
                    )
                )
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )
