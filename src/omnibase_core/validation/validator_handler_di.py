# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorHandlerDi -- K1 ``handler_di`` entry (OMN-21531, plan task T0.3).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_handler_di`: reads one
module and hands its path and source with the contract's rule rows to the pure checker.
The scope (every ``.py`` under ``handlers/`` and ``nodes/`` plus ``*_cli.py``) is the
contract's ``target_patterns``; a file handed in by name outside it is not judged.

The ``baseline_ratchet`` row names the shrink-only baseline of findings that predate K1
(``baseline_path``, read when it exists) and the revision it may not grow against
(``base_ref``). Entries follow code when git records a rename or copy, sharing the
origin's budget even when the move was already committed with a stale entry. Handing
the baseline file itself to the validator checks growth and rejects entries for
missing files; removed files must have their entries dropped.

Usage (pre-commit hook ``handler-di-gate``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_handler_di:ValidatorHandlerDi <files...>
"""

from __future__ import annotations

import fnmatch
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_handler_di_module_fact import (
    ModelHandlerDiModuleFact,
)
from omnibase_core.validation.checker_baseline_moves import parse_name_status_moves
from omnibase_core.validation.checker_handler_di import (
    RULE_BASELINE,
    apply_baseline,
    baseline_growth,
    baseline_missing,
    check_module,
    parse_baseline,
)
from omnibase_core.validation.checker_rule_parameters import rule_int, rule_string
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = ["ValidatorHandlerDi"]


class ValidatorHandlerDi(ValidatorBase):
    """Read one handler, node or CLI module and judge it against the contract rule rows."""

    validator_id: ClassVar[str] = "handler_di"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        root: Path | None = None,
        baseline: dict[str, int] | None = None,
        baseline_path: str | None = None,
    ) -> None:
        super().__init__(contract)
        self._root = (root or Path.cwd()).resolve()
        rules = {r.rule_id: r for r in self.contract.rules}
        # an enabled row with a missing or mistyped parameter raises here, at load
        check_module(ModelHandlerDiModuleFact("", ""), rules)
        self._baseline_path = ""
        self._baseline: dict[str, int] = {}
        row = rules.get(RULE_BASELINE)
        if row is not None and row.enabled:
            declared = rule_string(row, "baseline_path")
            self._baseline_path = baseline_path or declared
            self._base_ref = rule_string(row, "base_ref")
            self._move_similarity_percent = rule_int(row, "move_similarity_percent")
            rule_string(row, "missing_message")
            _probe_baseline_messages(rules)
            self._baseline = (
                baseline
                if baseline is not None
                else self._read_baseline(self._baseline_path)
            )

    def _read_baseline(self, relative: str) -> dict[str, int]:
        file = self._root / relative
        return (
            parse_baseline(file.read_text(encoding="utf-8")) if file.is_file() else {}
        )

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        return [p for p in super()._resolve_targets(targets) if self._in_scope(p)]

    def _in_scope(self, path: Path) -> bool:
        key = self._key(path)
        if self._baseline_path and key == self._baseline_path:
            return True
        return any(fnmatch.fnmatch(f"/{key}", p) for p in self.contract.target_patterns)

    def _key(self, path: Path) -> str:
        resolved = path.resolve()
        return (
            resolved.relative_to(self._root).as_posix()
            if resolved.is_relative_to(self._root)
            else resolved.as_posix()
        )

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        key = self._key(path)
        if self._baseline_path and key == self._baseline_path:
            base_text = self._base_text()
            base = parse_baseline(base_text)
            growth = (
                baseline_growth(
                    self._baseline, base, Path(key), rules, self._moves(base)
                )
                if base_text is not None
                else ()  # first install: no base baseline to grow from
            )
            missing = baseline_missing(
                self._baseline,
                lambda p: (self._root / p).is_file(),
                Path(key),
                rules,
            )
            return (*growth, *missing)
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ()
        issues = check_module(ModelHandlerDiModuleFact(key, source), rules)
        if not self._baseline_path:
            return issues
        return apply_baseline(Path(key), issues, self._baseline.get(key, 0), rules)

    def _base_text(self) -> str | None:
        """The baseline as the base revision holds it; ``None`` when it has none yet."""
        return self._git_text("show", f"{self._base_ref}:{self._baseline_path}")

    def _git_text(self, *args: str) -> str | None:
        """Read git output, treating unavailable git or a failed command as absent."""
        try:
            shown = subprocess.run(
                ["git", *args],
                cwd=self._root,
                env=scrub_git_location_env(),
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        return shown.stdout if shown.returncode == 0 else None

    def _moves(self, base: Mapping[str, int]) -> dict[str, str]:
        """Moves against the base revision, plus committed moves of stale origins."""
        diff_args = (
            "diff",
            f"-M{self._move_similarity_percent}%",
            f"-C{self._move_similarity_percent}%",
            "--find-copies-harder",
            "--name-status",
        )
        moves = parse_name_status_moves(
            self._git_text(*diff_args, self._base_ref, "--") or ""
        )
        diffs: dict[str, str] = {}
        for path in sorted(base):
            if self._git_text("cat-file", "-e", f"{self._base_ref}:{path}") is not None:
                continue
            commit = self._git_text(
                "log",
                "-1",
                "--no-renames",
                "--diff-filter=D",
                "--format=%H",
                self._base_ref,
                "--",
                path,
            )
            if not commit or not (commit := commit.strip()):
                continue
            if commit not in diffs:
                diffs[commit] = (
                    self._git_text(*diff_args, f"{commit}^", commit, "--") or ""
                )
            for destination, origin in parse_name_status_moves(diffs[commit]).items():
                if origin == path:
                    moves.setdefault(destination, origin)
        # a move leaves nothing behind: a file that is still in the tree keeps its own entry and
        # frees no budget for a similar-looking new file to claim
        return {d: o for d, o in moves.items() if not (self._root / o).exists()}


def _probe_baseline_messages(rules: dict[str, ModelValidatorRule]) -> None:
    """Format each baseline message once, so a missing message fails at load."""
    probe = Path("probe")
    issue = ModelValidationIssue(
        severity=rules[RULE_BASELINE].severity, message="probe", code="probe"
    )
    apply_baseline(probe, (issue, issue), 1, rules)
    apply_baseline(probe, (), 1, rules)
    baseline_growth({"probe": 1}, {}, probe, rules)
    baseline_missing({"probe": 1}, lambda _: False, probe, rules)
