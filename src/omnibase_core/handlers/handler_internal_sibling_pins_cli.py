# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the internal sibling pin check (OMN-19998).

Backs the ``check-internal-sibling-pins`` pre-commit hook, the reusable
``internal-sibling-pins.yml`` workflow every consumer inherits, and manual runs.
All I/O happens here: the pyproject reads (``node_source_file_gather_effect``),
the contract read and the report write (``node_validation_report_write_effect``).
The verdict is the pure ``HandlerInternalSiblingPins``.

The contract is the one omnibase_core ships in the package, so a consumer reads
it from the validator's pinned checkout and cannot edit it.

Usage::

    check-internal-sibling-pins --root ../omniclaude      # the root pyproject.toml
    check-internal-sibling-pins pyproject.toml            # pre-commit staged files

Exit codes: 0 -- PASS; 1 -- FAIL/ERROR.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from omnibase_core.handlers.handler_internal_sibling_pins import (
    VALIDATOR_ID,
    HandlerInternalSiblingPins,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import (
    ModelSourceFile,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_contract import (
    ModelInternalSiblingPinsContract,
)
from omnibase_core.models.version_drift.model_internal_sibling_pins_input import (
    ModelInternalSiblingPinsInput,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["DEFAULT_CONTRACT", "load_contract", "main"]

DEFAULT_CONTRACT: Final[Path] = (
    Path(__file__).parent.parent / "contracts" / "internal_sibling_pins.yaml"
)


def load_contract(path: Path = DEFAULT_CONTRACT) -> ModelInternalSiblingPinsContract:
    """The internal sibling pin contract at ``path``."""
    return load_yaml_content_as_model(
        path.read_text("utf-8"), ModelInternalSiblingPinsContract
    )


def _relative(root: Path, path: str) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError:
        return path


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Returns 0 on PASS, 1 on FAIL/ERROR."""
    parser = argparse.ArgumentParser(
        prog="check-internal-sibling-pins",
        description=(
            "Refuse a release, bare-sha or branch pin of an internal sibling; "
            "internal siblings resolve from dev merge tags (OMN-19998)."
        ),
    )
    parser.add_argument(
        "filenames", nargs="*", help="pyproject.toml files (pre-commit mode)."
    )
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--contract",
        default=str(DEFAULT_CONTRACT),
        help="Contract path (default: the one packaged with omnibase_core).",
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the report JSON here."
    )
    parsed = parser.parse_args(argv)

    root = Path(parsed.root).resolve()
    names = (
        [n for n in parsed.filenames if Path(n).name == "pyproject.toml"]
        if parsed.filenames
        else ["pyproject.toml"]
    )
    if not names:
        _out("OK: no pyproject.toml among the staged files")
        return 0
    gathered = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=str(root),
            include_patterns=["pyproject.toml"],
            explicit_paths=[str(root / name) for name in names],
        )
    )
    files = [
        ModelSourceFile(path=_relative(root, file.path), source=file.source)
        for file in gathered.files
    ]
    runtime_errors = [
        f"{_relative(root, skip.path)}: {skip.reason}" for skip in gathered.skipped
    ]
    if runtime_errors:
        _write_report(
            parsed.report_json,
            ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, tuple(runtime_errors)
            ),
        )
        for message in runtime_errors:
            _out(f"ERROR: {message}")
        return 1

    report = HandlerInternalSiblingPins().handle(
        ModelInternalSiblingPinsInput(
            files=tuple(files),
            contract=load_contract(Path(parsed.contract)),
        )
    )
    _write_report(parsed.report_json, report)
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status == "PASS":
        _out(
            f"OK: {len(files)} pyproject file(s) pin every internal sibling "
            "to a dev merge tag"
        )
        return 0
    if report.findings:
        _out(f"remediation: {report.findings[0].remediation}")
    _out(
        f"{report.overall_status}: an internal sibling is pinned to a release, a "
        "sha or a branch instead of a dev merge tag"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
