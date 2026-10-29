# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI I/O for the pre-commit pin-parity check (OMN-21495).

Read rule data and config source, resolve commit times from a history checkout
or the read-only pre-commit cache, then run the pure handler and write its report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

import yaml

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_precommit_cache_adapter import (
    cache_commit_times,
    commit_time,
)
from omnibase_core.handlers.handler_precommit_pin_parity import (
    HandlerPrecommitPinParity,
)
from omnibase_core.handlers.handler_precommit_pin_parity_rules import (
    VALIDATOR_ID,
    extract_pins,
    normalize_repo_url,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.precommit_pins import (
    ModelPrecommitPinParityInput,
    ModelPrecommitPinRules,
    ModelPrecommitRevTime,
)
from omnibase_core.models.precommit_pins.model_precommit_pin import ModelPrecommitPin
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

__all__ = ["DEFAULT_CONFIG", "DEFAULT_RULES", "main"]

DEFAULT_CONFIG: Final[str] = ".pre-commit-config.yaml"
DEFAULT_RULES: Final[Path] = (
    Path(__file__).parent.parent / "contracts" / "precommit_pin_parity.yaml"
)


def _rev_times(
    pins: tuple[ModelPrecommitPin, ...],
    rules: ModelPrecommitPinRules,
    history_repo: Path | None,
    pre_commit_home: Path,
) -> tuple[ModelPrecommitRevTime, ...]:
    """Resolve only named repositories with multiple distinct revisions."""
    named = {normalize_repo_url(repo) for repo in rules.hook_repos}
    groups: dict[str, set[str]] = {}
    for pin in pins:
        repo = normalize_repo_url(pin.repo)
        if repo in named:
            groups.setdefault(repo, set()).add(pin.rev)
    candidates = tuple(
        pin for pin in pins if len(groups.get(normalize_repo_url(pin.repo), ())) > 1
    )
    times: dict[str, int] = {}
    if history_repo is None:
        times = cache_commit_times(pre_commit_home, candidates)
    else:
        for rev in sorted({pin.rev for pin in candidates}):
            committed_at = commit_time(history_repo, f"{rev}^{{commit}}")
            if committed_at is not None:
                times[rev] = committed_at
    return tuple(
        ModelPrecommitRevTime(rev=rev, committed_at=committed_at)
        for rev, committed_at in sorted(times.items())
    )


def _out(line: str) -> None:
    sys.stdout.write(line + "\n")


def _write_report(path: str | None, report: ModelValidationReport) -> None:
    if path is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=path, report=report)
        )


def _runtime_failure(errors: list[str], report_path: str | None) -> int:
    report = ModelValidationReport.from_runtime_errors(VALIDATOR_ID, tuple(errors))
    _write_report(report_path, report)
    for message in errors:
        _out(f"ERROR: {message}")
    _out("ERROR: pre-commit pin-parity check could not complete")
    return 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry. Return 0 on PASS/WARN, 1 on FAIL/ERROR."""
    parser = argparse.ArgumentParser(
        prog="check-precommit-pin-parity",
        description="Refuse older pins of shared hook repositories (OMN-21495).",
    )
    parser.add_argument(
        "filenames", nargs="*", help="Repository-relative staged files."
    )
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument(
        "--config", default=DEFAULT_CONFIG, help="Config path relative to --root."
    )
    parser.add_argument(
        "--rules", default=str(DEFAULT_RULES), help="Packaged pin-parity rule data."
    )
    parser.add_argument(
        "--history-repo",
        type=Path,
        default=None,
        help="Checkout holding the pinned revs.",
    )
    parser.add_argument(
        "--pre-commit-home",
        type=Path,
        default=Path.home() / ".cache" / "pre-commit",
        help="Pre-commit cache directory used when no history checkout is supplied.",
    )
    parser.add_argument(
        "--report-json", default=None, help="Write the report JSON here."
    )
    parsed = parser.parse_args(argv)

    try:
        root = Path(parsed.root).resolve()
        config = (root / parsed.config).resolve()
        if parsed.filenames and not any(
            (root / filename).resolve() == config for filename in parsed.filenames
        ):
            return 0
        rules = load_and_validate_yaml_model(Path(parsed.rules), ModelPrecommitPinRules)
        source = config.read_text(encoding="utf-8")
        pins = extract_pins(source)
        report = HandlerPrecommitPinParity().handle(
            ModelPrecommitPinParityInput(
                rules=rules,
                path=parsed.config,
                source=source,
                rev_times=_rev_times(
                    pins, rules, parsed.history_repo, parsed.pre_commit_home
                ),
            )
        )
    except (OSError, ValueError, yaml.YAMLError, ModelOnexError) as exc:
        return _runtime_failure(
            [f"cannot check pre-commit config {parsed.config!r}: {exc}"],
            parsed.report_json,
        )

    _write_report(parsed.report_json, report)
    for finding in report.findings:
        _out(f"{finding.severity}: {finding.message}")
    if report.overall_status in ("PASS", "WARN"):
        _out("OK: pre-commit pin-parity check passed")
        return 0
    _out(
        f"{report.overall_status}: pre-commit pin-parity check failed; see findings above"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
