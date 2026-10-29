# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorCheckerRuleData -- K10 ``checker_rule_data`` entry (OMN-21503).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_checker_rule_data`:
reads the module and the names beside it, hands them to the pure checker.

    python -m omnibase_core.validation.validator_checker_rule_data [--baseline FILE [--base-ref REF]] [paths...]

``--baseline`` holds the rule tables that sat in checkers before K10 (burn-down children
of OMN-21503); ``--base-ref`` also refuses a baseline entry the base revision lacks, and limits
``validator_outside_generic_format`` to modules that revision does not hold (new validators).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_checker_rule_data_module_fact import (
    ModelCheckerRuleDataModuleFact,
)
from omnibase_core.validation.checker_checker_rule_data import (
    apply_baseline,
    baseline_growth,
    check_module,
    parse_baseline,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorCheckerRuleData(ValidatorBase):
    """Refuse rule tables held in a checker, and validators outside the generic format."""

    validator_id: ClassVar[str] = "checker_rule_data"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        baseline: Mapping[str, int] | None = None,
        base_ref: str = "",
        root: Path | None = None,
    ) -> None:
        super().__init__(contract)
        self._base_ref = base_ref
        self._baseline = dict(baseline) if baseline is not None else None
        self._root = (root or Path.cwd()).resolve()

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        fact = ModelCheckerRuleDataModuleFact(
            new_in_change=not (
                self._base_ref and _exists_at(self._base_ref, self._key(path))
            ),
            name=path.name,
            posix_path=path.as_posix(),
            source=path.read_text(encoding="utf-8", errors="replace"),
            sibling_names=_names_in(path.parent),
            contract_names=_names_in(path.parent / "contracts"),
        )
        rules = {r.rule_id: r for r in contract.rules}
        issues = check_module(path, fact, rules)
        if self._baseline is None:
            return issues
        key = self._key(path)
        return apply_baseline(Path(key), issues, self._baseline.get(key, 0), rules)

    def _key(self, path: Path) -> str:
        resolved = path.resolve()
        return (
            resolved.relative_to(self._root).as_posix()
            if resolved.is_relative_to(self._root)
            else path.as_posix()
        )

    @classmethod
    def main(cls) -> int:
        """CLI entry: the generic targets plus the baseline and its base revision."""
        parser = argparse.ArgumentParser(
            description=f"Run {cls.validator_id} validator"
        )
        parser.add_argument("targets", nargs="*", type=Path)
        parser.add_argument("--baseline", type=Path, default=None)
        parser.add_argument("--base-ref", default="")
        args = parser.parse_args()
        baseline = (
            parse_baseline(args.baseline.read_text(encoding="utf-8"))
            if args.baseline is not None
            else None
        )
        if args.base_ref and not _ref_exists(args.base_ref):
            sys.stderr.write(f"base ref {args.base_ref!r} is not in the clone\n")
            return 1
        validator = cls(baseline=baseline, base_ref=args.base_ref)
        result = validator.validate(args.targets or [Path()])
        growth: tuple[ModelValidationIssue, ...] = ()
        if baseline is not None and args.base_ref:
            base_text = _baseline_at(args.base_ref, args.baseline)
            if base_text is not None:
                rules = {r.rule_id: r for r in validator.contract.rules}
                growth = baseline_growth(
                    baseline, parse_baseline(base_text), args.baseline, rules
                )
        for issue in (*result.issues, *growth):
            sys.stdout.write(
                f"{issue.severity.value.upper()}: {issue.file_path}: {issue.message}\n"
            )
        return 1 if growth else validator.get_exit_code(result)


def _names_in(directory: Path) -> frozenset[str]:
    if not directory.is_dir():
        return frozenset()
    return frozenset(p.name for p in directory.iterdir())


def _exists_at(ref: str, key: str) -> bool:
    probe = subprocess.run(
        ["git", "cat-file", "-e", f"{ref}:{key}"],
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


def _ref_exists(ref: str) -> bool:
    probe = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"],
        capture_output=True,
        check=False,
    )
    return probe.returncode == 0


def _baseline_at(ref: str, baseline: Path) -> str | None:
    """The baseline as the base revision holds it; ``None`` when it has none yet."""
    shown = subprocess.run(
        ["git", "show", f"{ref}:{baseline.as_posix()}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return shown.stdout if shown.returncode == 0 else None


if __name__ == "__main__":
    sys.exit(ValidatorCheckerRuleData.main())
