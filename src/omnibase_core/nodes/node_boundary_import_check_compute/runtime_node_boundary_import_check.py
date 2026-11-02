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
from importlib import resources
from pathlib import PurePath
from typing import cast

from dependency_injector import providers

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.contracts.subcontracts.model_protocol_dependency import (
    ModelProtocolDependency,
)
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
from omnibase_core.nodes.node_boundary_import_check_effect._git_file_listing_interface import (
    GitFileListingInterface,
)
from omnibase_core.nodes.node_boundary_import_check_effect._source_file_gather_interface import (
    SourceFileGatherInterface,
)
from omnibase_core.nodes.node_boundary_import_check_effect._validation_report_write_interface import (
    ValidationReportWriteInterface,
)
from omnibase_core.nodes.node_boundary_import_check_effect.handler import (
    NodeBoundaryImportCheckEffect,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler import (
    NodeGitFileListingEffect,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates


def build_container() -> ModelONEXContainer:
    """Bind the boundary effect's declared protocols to their canonical effects."""
    container = ModelONEXContainer(enable_service_registry=False)
    configured = False
    try:
        registry = container.initialize_service_registry(
            create_default_registry_config().model_copy(
                update={"lazy_loading_enabled": False}
            )
        )
        bindings = {
            f"{token.__module__}:{token.__name__}": (token, implementation)
            for token, implementation in (
                (
                    cast("type[object]", GitFileListingInterface),
                    NodeGitFileListingEffect,
                ),
                (
                    cast("type[object]", SourceFileGatherInterface),
                    NodeSourceFileGatherEffect,
                ),
                (
                    cast("type[object]", ValidationReportWriteInterface),
                    NodeValidationReportWriteEffect,
                ),
            )
        }
        contract = resources.files(
            "omnibase_core.nodes.node_boundary_import_check_effect"
        ).joinpath("contract.yaml")
        document = load_yaml_mapping_no_duplicates(
            contract.read_text(encoding="utf-8"), source=str(contract)
        )
        declared = document["protocol_dependencies"]
        if not isinstance(declared, list):
            raise ModelOnexError(
                message="Boundary import protocol_dependencies must be a list",
                error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
            )
        dependencies = [
            ModelProtocolDependency.model_validate(item) for item in declared
        ]
        for dependency in dependencies:
            if dependency.protocol not in bindings:
                raise ModelOnexError(
                    message=f"Unbound boundary import protocol: {dependency.protocol}",
                    error_code=EnumCoreErrorCode.PROTOCOL_CONFIGURATION_ERROR,
                )
            token, implementation = bindings[dependency.protocol]
            run_coro_sync(
                registry.register_service(
                    token,
                    implementation,
                    EnumServiceLifecycle.SINGLETON,
                    EnumInjectionScope.GLOBAL,
                )
            )
        run_coro_sync(
            registry.register_service(
                NodeBoundaryImportCheckCompute,
                NodeBoundaryImportCheckCompute,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
        effect = providers.Factory(NodeBoundaryImportCheckEffect, container=container)
        run_coro_sync(
            registry.register_instance(NodeBoundaryImportCheckEffect, effect())
        )
        configured = True
        return container
    finally:
        if not configured:
            container.close()


def main(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run with injected services, closing only the container owned by this call."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(argv, container)
    finally:
        if owned:
            container.close()


def _run(argv: list[str] | None, container: ModelONEXContainer) -> int:
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
    effect = container.get_service(NodeBoundaryImportCheckEffect)
    compute = container.get_service(NodeBoundaryImportCheckCompute)
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
        report = compute.handle(request)
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
            elif not request.base_baseline_present and not request.bootstrap:
                sys.stderr.write(
                    "Refusing baseline adoption: missing base baseline; pass --bootstrap.\n"
                )
                report = ModelValidationReport.from_findings(
                    findings=report.findings
                    + (
                        ModelValidationFindingEmbed(
                            validator_id=VALIDATOR_ID,
                            severity="FAIL",
                            rule_id="baseline-bootstrap-unflagged",
                            location=request.baseline_path,
                            message="Writing with no base baseline requires --bootstrap.",
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
                report = compute.handle(
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
