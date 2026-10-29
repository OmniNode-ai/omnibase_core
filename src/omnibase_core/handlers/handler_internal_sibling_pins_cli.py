# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime for the internal sibling pin check (OMN-19998).

Backs the ``check-internal-sibling-pins`` pre-commit hook, the reusable
``internal-sibling-pins.yml`` workflow every consumer inherits, and manual runs.
All I/O happens here: the pyproject reads (``node_source_file_gather_effect``),
the contract read, sibling tag reads via git, and the report write
(``node_validation_report_write_effect``). ``--no-staleness`` skips remote
tag reads for offline pre-commit use.
The verdict is the pure ``HandlerInternalSiblingPins``.

The contract is the one omnibase_core ships in the package, so a consumer reads
it from the validator's pinned checkout and cannot edit it.

Usage::

    check-internal-sibling-pins --root ../omniclaude      # the root pyproject.toml
    check-internal-sibling-pins --no-staleness pyproject.toml  # offline staged files

Exit codes: 0 -- PASS; 1 -- FAIL/ERROR.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Final

from omnibase_core.handlers.handler_internal_sibling_pins import (
    VALIDATOR_ID,
    HandlerInternalSiblingPins,
    declared_sibling_repos,
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
from omnibase_core.models.version_drift.model_sibling_dev_tags import (
    ModelSiblingDevTags,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["DEFAULT_CONTRACT", "load_contract", "main", "read_dev_tags"]

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


def read_dev_tags(
    contract: ModelInternalSiblingPinsContract, repo: str
) -> ModelSiblingDevTags:
    """Read one sibling's dev tags; git errors propagate to the CLI boundary."""
    result = subprocess.run(
        [
            "git",
            "ls-remote",
            "--tags",
            f"{contract.repo_url(repo)}.git",
            "refs/tags/dev-*",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=contract.ls_remote_timeout_seconds,
    )
    prefix = "refs/tags/"
    tags = set()
    for line in result.stdout.splitlines():
        fields = line.split()
        if (
            len(fields) == 2
            and fields[1].startswith(prefix)
            and not fields[1].endswith("^{}")
        ):
            tags.add(fields[1].removeprefix(prefix))
    return ModelSiblingDevTags(repo=repo, tags=tuple(sorted(tags)))


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
            "Require internal sibling dev merge tags within the contract's "
            "staleness bounds (OMN-19998, OMN-21478)."
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
    parser.add_argument(
        "--no-staleness",
        action="store_true",
        help="Skip remote tag reads and staleness evaluation (offline mode).",
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

    contract = load_contract(Path(parsed.contract))
    dev_tags = None
    if not parsed.no_staleness:
        try:
            repos = {
                repo
                for file in files
                for repo in declared_sibling_repos(tomllib.loads(file.source), contract)
            }
            dev_tags = tuple(read_dev_tags(contract, repo) for repo in sorted(repos))
        except (OSError, subprocess.SubprocessError, tomllib.TOMLDecodeError) as exc:
            message = f"cannot read sibling dev tags: {exc}"
            _write_report(
                parsed.report_json,
                ModelValidationReport.from_runtime_errors(VALIDATOR_ID, (message,)),
            )
            _out(f"ERROR: {message}")
            return 1
    report = HandlerInternalSiblingPins().handle(
        ModelInternalSiblingPinsInput(
            files=tuple(files),
            contract=contract,
            dev_tags=dev_tags,
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
        f"{report.overall_status}: an internal sibling pin violates the dev merge "
        "tag contract"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
