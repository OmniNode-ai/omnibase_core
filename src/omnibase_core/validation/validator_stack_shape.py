# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorStackShape -- allowlist stack-shape entry (OMN-21891, one-runtime plan task T1).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_stack_shape`. The caller's data
file (``baseline_ratchet.data_path`` of the contract, or the ``data_path`` argument) names the
runtime, the allowed dependencies, the one-shots, each lane's compose file set and the baseline.
Handing the validator the data file or any compose file of a lane judges the whole stack once;
a file outside every lane is not judged.

The baseline is held to the revision ``base_ref`` (the merge base in CI): once the data file exists
there, an entry absent from it fails, following its compose file when git records a move.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_stack_shape_data import (
    ModelStackShapeData,
)
from omnibase_core.validation.checker_baseline_moves import parse_name_status_moves
from omnibase_core.validation.checker_rule_parameters import rule_int, rule_string
from omnibase_core.validation.checker_stack_shape import (
    RULE_BASELINE,
    RULE_DATA_INVALID,
    RULE_FILE_MISSING,
    RULE_FILE_UNREADABLE,
    baseline_growth,
    baseline_keys,
    check_baseline,
    check_compose,
    compose_services,
    lane_files,
    parse_stack_shape_data,
    report,
    validate_rules,
)
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = ["ValidatorStackShape"]


class ValidatorStackShape(ValidatorBase):
    """Judge every lane's compose files against the allowlist the data file holds."""

    validator_id: ClassVar[str] = "stack_shape"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        root: Path | None = None,
        data_path: str | None = None,
        base_ref: str | None = None,
    ) -> None:
        super().__init__(contract)
        self._root = (root or Path.cwd()).resolve()
        rules = {r.rule_id: r for r in self.contract.rules}
        validate_rules(rules)
        row = rules[RULE_BASELINE]
        self._data_path = data_path or rule_string(row, "data_path")
        self._base_ref = base_ref or rule_string(row, "base_ref")
        self._similarity = rule_int(row, "move_similarity_percent")

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        data_file = self._root / self._data_path
        if not data_file.is_file():
            return []
        stack = {data_file.resolve()}
        stack.update(self._compose_paths(data_file))
        if any(t.resolve() in stack for t in targets if t.exists()):
            return [data_file.resolve()]
        return []

    def _compose_paths(self, data_file: Path) -> set[Path]:
        try:
            data = parse_stack_shape_data(data_file.read_text(encoding="utf-8"))
        except ModelOnexError:
            return set()
        return {(self._root / f).resolve() for f in lane_files(data)}

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        try:
            data = parse_stack_shape_data(path.read_text(encoding="utf-8"))
        except ModelOnexError as exc:
            return report(rules, RULE_DATA_INVALID, self._data_path, reason=exc.message)
        issues: list[ModelValidationIssue] = []
        found: dict[str, list[str] | None] = {}
        for file, lanes in lane_files(data).items():
            target = self._root / file
            if not target.is_file():
                found[file] = None
                issues.extend(
                    report(rules, RULE_FILE_MISSING, file, lanes=", ".join(lanes))
                )
                continue
            try:
                services = compose_services(target.read_text(encoding="utf-8"), rules)
            except ModelOnexError as exc:
                found[file] = None
                issues.extend(
                    report(
                        rules,
                        RULE_FILE_UNREADABLE,
                        file,
                        lanes=", ".join(lanes),
                        reason=exc.message,
                    )
                )
                continue
            found[file] = list(services)
            issues.extend(check_compose(data, file, services, lanes, rules))
        issues.extend(check_baseline(data, found, rules))
        issues.extend(self._growth(data, rules))
        return tuple(issues)

    def _growth(
        self, data: ModelStackShapeData, rules: Mapping[str, ModelValidatorRule]
    ) -> tuple[ModelValidationIssue, ...]:
        base_text = self._git_text("show", f"{self._base_ref}:{self._data_path}")
        if base_text is None:
            return ()  # first install: no base baseline to grow from
        try:
            base = baseline_keys(parse_stack_shape_data(base_text), rules)
        except ModelOnexError:
            return ()
        return baseline_growth(baseline_keys(data, rules), base, self._moves(), rules)

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

    def _moves(self) -> dict[str, str]:
        """File moves against the base revision, for origins that no longer exist."""
        moves = parse_name_status_moves(
            self._git_text(
                "diff",
                f"-M{self._similarity}%",
                f"-C{self._similarity}%",
                "--name-status",
                self._base_ref,
                "--",
            )
            or ""
        )
        # a file that is still in the tree keeps its own entries and frees no budget
        return {d: o for d, o in moves.items() if not (self._root / o).exists()}
