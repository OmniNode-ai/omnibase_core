# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorBaselinedDetector -- per-file shrink-only baseline entry for the AST detectors (OMN-22005).

``ValidatorBase`` entry shared by ``validator_except_swallow``, ``validator_none_guard_publish`` and
``validator_import_none_fallback``: reads one module and hands its path and source with the contract's
rule rows to the subclass's pure checker, then holds the module to its entry in the baseline.

The ``baseline_ratchet`` row names the shrink-only baseline of findings that predate the refusal
(``baseline_path``, read when it exists) and the revision it may not grow against (``base_ref``).
Entries follow code when git records a rename or copy. Handing the baseline file itself to the
validator checks growth and rejects entries for missing files.
"""

from __future__ import annotations

import fnmatch
import subprocess
from abc import abstractmethod
from collections.abc import Mapping
from pathlib import Path
from typing import Self

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_baseline_moves import parse_name_status_moves
from omnibase_core.validation.checker_detector_common import parse_baseline
from omnibase_core.validation.checker_handler_di import (
    RULE_BASELINE,
    apply_baseline,
    baseline_growth,
    baseline_missing,
)
from omnibase_core.validation.checker_rule_parameters import rule_int, rule_string
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = ["ValidatorBaselinedDetector"]


class ValidatorBaselinedDetector(ValidatorBase):
    """Read one module and judge it against the rule rows and its baseline entry."""

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
        self._judge(Path("probe"), "", rules)
        self._baseline_path = ""
        self._baseline: dict[str, int] = {}
        row = rules.get(RULE_BASELINE)
        if row is not None and row.enabled:
            self._baseline_path = self._key(
                self._root / (baseline_path or rule_string(row, "baseline_path"))
            )
            self._base_ref = rule_string(row, "base_ref")
            self._move_similarity_percent = rule_int(row, "move_similarity_percent")
            rule_string(row, "missing_message")
            _probe_baseline_messages(rules)
            self._baseline = (
                baseline
                if baseline is not None
                else self._read_baseline(self._baseline_path)
            )

    @classmethod
    def with_baseline_file(cls, path: Path) -> Self:
        """The validator held to the per-file baseline in ``path`` (the hook's ``--baseline``)."""
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read baseline: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        return cls(baseline=parse_baseline(text), baseline_path=str(path))

    @abstractmethod
    def _judge(
        self, path: Path, source: str, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        """The pure checker over one module."""

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
            base_text = self._git_text(
                "show", f"{self._base_ref}:{self._baseline_path}"
            )
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
        issues = self._judge(Path(key), source, rules)
        if not self._baseline_path:
            return issues
        return apply_baseline(Path(key), issues, self._baseline.get(key, 0), rules)

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
