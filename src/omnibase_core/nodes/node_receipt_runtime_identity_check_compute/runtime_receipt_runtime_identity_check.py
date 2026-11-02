# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""CLI for the receipt runtime-identity gate (OMN-17308, OMN-21520).

Usage::

    python -m omnibase_core.nodes.node_receipt_runtime_identity_check_compute.runtime_receipt_runtime_identity_check \\
        --receipts-dir docs/evidence/receipts
    python -m omnibase_core.nodes.node_receipt_runtime_identity_check_compute.runtime_receipt_runtime_identity_check a.json b.json

Exit 0 clean, exit 1 on any violation, exit 2 when no target was given.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Final, cast

from omnibase_core.enums.enum_injection_scope import EnumInjectionScope
from omnibase_core.enums.enum_service_lifecycle import EnumServiceLifecycle
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)
from omnibase_core.models.dispatch.model_skill_result import (
    RUNTIME_IDENTITY_REQUIRED_FROM,
)
from omnibase_core.models.nodes.receipt_runtime_identity_check.model_receipt_runtime_identity_check_input import (
    ModelReceiptRuntimeIdentityCheckInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_receipt_runtime_identity_check_compute.handler import (
    NodeReceiptRuntimeIdentityCheckCompute,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_runtime_overlay import (
    HandlerValidatorRuntimeOverlay,
)
from omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run import (
    build_validator_container,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.validation.validator_receipt_runtime_identity import (
    DEFAULT_REQUIRED_PACKAGES,
    _is_scannable,
)

VALIDATOR_ID: Final[str] = "receipt-runtime-identity"

_NODE_RECEIPT_RUNTIME_IDENTITY_CHECK_COMPUTE_TOKEN = cast(
    "type[NodeReceiptRuntimeIdentityCheckCompute]",
    NodeReceiptRuntimeIdentityCheckCompute,
)


def _out(message: str) -> None:
    sys.stdout.write(message + "\n")


def _err(message: str) -> None:
    sys.stderr.write(message + "\n")


def _write_report(
    report_path: str | None,
    overlay_path: Path | None,
    findings: tuple[ModelValidationFindingEmbed, ...] = (),
    *,
    runtime_error: str | None = None,
) -> None:
    """Persist every verdict and its events through the overlay's report writer."""
    handler = HandlerValidatorRuntimeOverlay()
    settings = handler.settings()
    overlay = handler.load(overlay_path or handler.default_overlay_path())
    report = (
        ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (runtime_error,))
        if runtime_error is not None
        else ModelValidationReport.from_findings(
            findings=findings,
            request=ModelValidationRequestRef(profile=overlay.profile),
            validators_run=(VALIDATOR_ID,),
        )
    )
    # Container and bus lifecycle logs must not change the hook's CLI output.
    previous_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        container = build_validator_container(overlay)
        try:
            container.get_service(NodeValidationReportWriteEffect).handle(
                ModelValidationReportWriteInput(
                    report_path=report_path
                    or settings.default_report_path.format(validator_id=VALIDATOR_ID),
                    report=report,
                    repository=settings.default_repository,
                )
            )
        finally:
            container.close()
    finally:
        logging.disable(previous_disable)


def build_container() -> ModelONEXContainer:
    """Register the runtime's handlers and effects under their service tokens."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry(
        create_default_registry_config().model_copy(
            update={"lazy_loading_enabled": False}
        )
    )
    for token, implementation in (
        (
            _NODE_RECEIPT_RUNTIME_IDENTITY_CHECK_COMPUTE_TOKEN,
            NodeReceiptRuntimeIdentityCheckCompute,
        ),
    ):
        run_coro_sync(
            registry.register_service(
                token,
                implementation,
                EnumServiceLifecycle.SINGLETON,
                EnumInjectionScope.GLOBAL,
            )
        )
    return container


def main(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """Run the CLI with container-resolved services."""
    owned = container is None
    if container is None:
        container = build_container()
    try:
        return _run(argv, container)
    finally:
        if owned:
            container.close()


def _run(argv: list[str] | None, container: ModelONEXContainer) -> int:
    """CLI: exit non-zero on any runtime-identity violation.

    Exit codes:
        0 -- clean (including "every receipt found was grandfathered")
        1 -- one or more violations, each printed with rule + detail
    """
    parser = argparse.ArgumentParser(
        description=(
            "Runtime-identity gate (OMN-17308): fail receipts at schema "
            f">= {RUNTIME_IDENTITY_REQUIRED_FROM} that do not identify the "
            "process that produced them."
        )
    )
    parser.add_argument(
        "--receipts-dir",
        default=None,
        help="Directory tree to scan for *.json receipts.",
    )
    parser.add_argument(
        "--require-package",
        action="append",
        default=None,
        metavar="DIST",
        help=(
            "Distribution a stamp must speak about. Repeatable. Default: "
            f"{', '.join(DEFAULT_REQUIRED_PACKAGES)}."
        ),
    )
    parser.add_argument(
        "receipt_paths",
        nargs="*",
        help="Explicit receipt files to scan (pre-commit passes these).",
    )
    # Keep the existing no-target diagnostic, including its usage line.
    no_target_usage = parser.format_usage()
    parser.add_argument(
        "--report-json",
        default=None,
        metavar="PATH",
        help="Report path; the node contract's default when omitted",
    )
    parser.add_argument(
        "--overlay",
        type=Path,
        default=None,
        metavar="PATH",
        help="Validator-runtime overlay; the node contract's default when omitted",
    )
    args = parser.parse_args(argv)

    required: tuple[str, ...] = (
        tuple(args.require_package) if args.require_package else ()
    )

    explicit = [Path(p) for p in args.receipt_paths]
    if explicit:
        candidates = explicit
        target = f"{len(explicit)} explicit file(s)"
    elif args.receipts_dir is not None:
        root = Path(args.receipts_dir)
        if not root.exists():
            message = f"ERROR: --receipts-dir does not exist: {root}"
            _write_report(args.report_json, args.overlay, runtime_error=message)
            _err(message)
            return 1
        candidates = [p for p in sorted(root.rglob("*.json")) if _is_scannable(p)]
        target = str(root)
    else:
        # The only "no target" path, so a mis-wired hook fails loudly instead
        # of scanning nothing and reporting success — a gate that passes
        # because it was handed nothing is the vacuous-PASS failure class this
        # validator exists to close (OMN-14531).
        #
        # Spelled as an explicit usage-print + return rather than argparse's
        # parser.error(): error() terminates only by convention, which left
        # `candidates` and `target` provably-unbound to static analysis (CodeQL
        # py/uninitialized-local-variable, 3 alerts on PR #1634). A validator
        # whose own no-target path can raise UnboundLocalError fails in the
        # least legible way available to it — the operator sees a traceback
        # instead of the refusal the gate meant to give.
        message = "ERROR: pass receipt files, or --receipts-dir"
        _write_report(args.report_json, args.overlay, runtime_error=message)
        sys.stderr.write(no_target_usage)
        _err(message)
        return 2

    result = container.get_service(
        _NODE_RECEIPT_RUNTIME_IDENTITY_CHECK_COMPUTE_TOKEN
    ).handle(
        ModelReceiptRuntimeIdentityCheckInput(
            receipt_paths=tuple(str(p) for p in candidates),
            required_packages=required or None,
        )
    )
    violations = result.violations
    receipts = result.receipts_found
    _write_report(
        args.report_json,
        args.overlay,
        tuple(
            ModelValidationFindingEmbed(
                validator_id=VALIDATOR_ID,
                severity="FAIL",
                location=violation.path,
                rule_id=violation.rule.value,
                message=violation.detail,
            )
            for violation in violations
        ),
    )

    if not violations:
        _out(
            f"RUNTIME IDENTITY GATE PASSED: 0 violations across "
            f"{receipts} receipt(s) in {len(candidates)} JSON file(s) "
            f"under {target}"
        )
        return 0

    _out(f"RUNTIME IDENTITY GATE FAILED: {len(violations)} violation(s) in {target}:\n")
    for violation in violations:
        _out(f"  [{violation.rule.value}] {violation.path}")
        _out(f"    {violation.detail}")
        _out("")
    return 1


if __name__ == "__main__":
    sys.exit(main())
