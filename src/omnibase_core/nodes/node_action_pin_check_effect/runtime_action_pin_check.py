# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the action-pin check (OMN-17427, OMN-21518).

Backs the ``check-action-pins`` pre-commit hook and manual runs. All I/O
happens here, at the CLI boundary: overlay YAML loading, workflow discovery
and reads, the base-ref overlay read for the shrink-only ratchet, and the
report write, resolved from the container. The verdict is the pure
``HandlerActionPin``; its rule data is the ``action_pin`` validation contract.

Usage::

    python -m omnibase_core.nodes.node_action_pin_check_effect.runtime_action_pin_check
    python -m ...runtime_action_pin_check --root ../omnibase_core
    python -m ...runtime_action_pin_check .github/workflows/ci.yml
    python -m ...runtime_action_pin_check --ratchet-base-ref origin/dev --report-json r.json

Exit codes: 0 -- PASS or WARN only; 1 -- FAIL/ERROR, or the overlay grew.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Final

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.action_pins.model_action_pin_check_input import (
    ModelActionPinCheckInput,
)
from omnibase_core.models.action_pins.model_action_pin_overlay import (
    ModelActionPinOverlay,
)
from omnibase_core.models.action_pins.model_action_pin_rules import (
    ModelActionPinRules,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_action_pin_check_effect.handler_action_pin import (
    HandlerActionPin,
)
from omnibase_core.nodes.node_action_pin_check_effect.matcher_action_pin import (
    extract_uses,
    is_candidate,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_run_coro_sync import run_coro_sync
from omnibase_core.utils.util_safe_yaml_loader import (
    load_and_validate_yaml_model,
    load_yaml_content_as_model,
)
from omnibase_core.validation.checker_action_pin import action_pin_rules
from omnibase_core.validation.validator_action_pin import ValidatorActionPin
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = [
    "DEFAULT_OVERLAY",
    "build_container",
    "load_rules",
    "main",
    "overlay_exception_growth",
]

DEFAULT_OVERLAY: Final[str] = ".action-pin-overlay.yaml"


def load_rules() -> ModelActionPinRules:
    """The rule data of the ``action_pin`` validation contract."""
    return action_pin_rules({r.rule_id: r for r in ValidatorActionPin().contract.rules})


def build_container() -> ModelONEXContainer:
    """The composition root: a container with the report writer registered."""
    container = ModelONEXContainer(enable_service_registry=False)
    registry = container.initialize_service_registry()
    run_coro_sync(
        registry.register_instance(
            NodeValidationReportWriteEffect, NodeValidationReportWriteEffect()
        )
    )
    return container


def overlay_exception_growth(
    current: ModelActionPinOverlay,
    base: ModelActionPinOverlay | None,
) -> list[str]:
    """Return exceptions added over the base; an absent base is introduction."""
    if base is None:
        return []
    base_uses = {exception.uses for exception in base.known_exceptions}
    return [
        f"overlay grew: known exception {exception.uses} is not in the base overlay"
        for exception in current.known_exceptions
        if exception.uses not in base_uses
    ]


def gather(
    root: Path, filenames: list[str], rules: ModelActionPinRules
) -> tuple[list[ModelSourceFile], list[str]]:
    """Read candidate workflows directly, retaining repository-relative paths."""
    if filenames:
        relative = [filename for filename in filenames if is_candidate(filename, rules)]
    else:
        workflows = root / rules.workflow_dir
        if not workflows.is_dir():
            return [], [
                f"missing workflows directory {workflows}: a full-tree run that "
                "scans nothing is ERROR, never PASS"
            ]
        relative = sorted(
            path.relative_to(root).as_posix()
            for pattern in (f"*{suffix}" for suffix in rules.workflow_suffixes)
            for path in workflows.glob(pattern)
        )

    files: list[ModelSourceFile] = []
    errors: list[str] = []
    for filename in relative:
        try:
            source = (root / filename).read_text(encoding="utf-8")
            files.append(ModelSourceFile(path=filename, source=source))
        except (OSError, ValueError, ModelOnexError) as exc:
            errors.append(f"{filename}: read error: {exc}")
    return files, errors


def _ref_exists(root: Path, ref: str) -> bool:
    return (
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "rev-parse",
                "--verify",
                "--quiet",
                f"{ref}^{{commit}}",
            ],
            capture_output=True,
            text=True,
            check=False,
            env=scrub_git_location_env(),
        ).returncode
        == 0
    )


def _base_overlay(root: Path, ref: str, overlay: str) -> ModelActionPinOverlay | None:
    """The overlay at ``ref``; None only when ``ref`` genuinely has no such file."""
    listed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", ref, "--", overlay],
        capture_output=True,
        text=True,
        check=False,
        env=scrub_git_location_env(),
    )
    if listed.returncode != 0:
        raise ModelOnexError(
            message=f"cannot list {overlay} at {ref}: {listed.stderr.strip()}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
        )
    if not listed.stdout.strip():
        return None
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{overlay}"],
        capture_output=True,
        text=True,
        check=False,
        env=scrub_git_location_env(),
    )
    if shown.returncode != 0:
        raise ModelOnexError(
            message=f"cannot read {overlay} at {ref}: {shown.stderr.strip()}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
        )
    return load_yaml_content_as_model(shown.stdout, ModelActionPinOverlay)


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def _write_report(
    container: ModelONEXContainer, path: str | None, report: ModelValidationReport
) -> None:
    if path is not None:
        container.get_service(NodeValidationReportWriteEffect).handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _runtime_failure(
    container: ModelONEXContainer,
    rules: ModelActionPinRules,
    errors: list[str],
    report_path: str | None,
) -> int:
    report = ModelValidationReport.from_runtime_errors(
        rules.report_validator_name, tuple(errors)
    )
    _write_report(container, report_path, report)
    for message in errors:
        _out(f"ERROR: {message}")
    _out("ERROR: action-pin check could not complete")
    return 1


def main(
    argv: list[str] | None = None, *, container: ModelONEXContainer | None = None
) -> int:
    """CLI entry. Return 0 on PASS/WARN, 1 on FAIL/ERROR or overlay growth."""
    parser = argparse.ArgumentParser(
        prog="check-action-pins",
        description=(
            "Require full commit sha pins for third-party actions and "
            "overlay-approved dev-merge tags for first-party actions (OMN-17427)."
        ),
    )
    parser.add_argument(
        "filenames", nargs="*", help="Repository-relative staged files."
    )
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--overlay",
        default=DEFAULT_OVERLAY,
        help=f"Overlay path relative to --root (default: {DEFAULT_OVERLAY})",
    )
    parser.add_argument(
        "--ratchet-base-ref",
        default=None,
        metavar="REF",
        help="Refuse known exceptions this ref's overlay does not have.",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        metavar="PATH",
        help="Write the report JSON here.",
    )
    parsed = parser.parse_args(argv)

    rules = load_rules()
    if parsed.filenames and not any(
        is_candidate(filename, rules) for filename in parsed.filenames
    ):
        return 0

    container = container or build_container()
    try:
        root = Path(parsed.root).resolve()
        overlay = load_and_validate_yaml_model(
            root / parsed.overlay, ModelActionPinOverlay
        )
    except (OSError, ValueError, ModelOnexError) as exc:
        return _runtime_failure(
            container,
            rules,
            [f"cannot load overlay {parsed.overlay!r}: {exc}"],
            parsed.report_json,
        )

    try:
        files, runtime_errors = gather(root, parsed.filenames, rules)
    except (OSError, ValueError, ModelOnexError) as exc:
        return _runtime_failure(
            container,
            rules,
            [f"cannot scan workflows under {root}: {exc}"],
            parsed.report_json,
        )

    if not parsed.filenames and not runtime_errors:
        if not any(True for file in files for _ in extract_uses(file.source, rules)):
            runtime_errors.append(
                f"zero uses: lines under {root / rules.workflow_dir}: "
                "a full-tree run that scans nothing is ERROR, never PASS"
            )

    if parsed.ratchet_base_ref:
        try:
            if not _ref_exists(root, parsed.ratchet_base_ref):
                runtime_errors.append(
                    f"ratchet base ref {parsed.ratchet_base_ref!r} is not in the "
                    "clone; fetch it, since a ratchet with no base is never a pass"
                )
            else:
                overlay_path = (root / parsed.overlay).relative_to(root).as_posix()
                base = _base_overlay(root, parsed.ratchet_base_ref, overlay_path)
                runtime_errors.extend(overlay_exception_growth(overlay, base))
        except (OSError, ValueError, ModelOnexError) as exc:
            runtime_errors.append(
                f"cannot check overlay against ratchet base ref "
                f"{parsed.ratchet_base_ref!r}: {exc}"
            )

    if runtime_errors:
        return _runtime_failure(container, rules, runtime_errors, parsed.report_json)

    report = HandlerActionPin().handle(
        ModelActionPinCheckInput(
            rules=rules,
            overlay=overlay,
            files=tuple(files),
            report_stale_exceptions=not parsed.filenames,
        )
    )
    _write_report(container, parsed.report_json, report)

    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")

    if report.overall_status in ("PASS", "WARN"):
        _out(f"OK: action-pin check passed ({len(files)} files scanned)")
        return 0

    _out(f"{report.overall_status}: action-pin check failed; see findings above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
