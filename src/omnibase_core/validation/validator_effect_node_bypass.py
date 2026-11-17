# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorEffectNodeBypass -- ``effect_node_bypass`` entry (OMN-24432).

The ``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_effect_node_bypass`. With no count
file every bypass found is a finding. Held to a count file (``--baseline``), the whole run's findings are
one number: it may not exceed the file, may not sit below it, and the file may not be raised against the
base revision; the ``count_ratchet`` row of ``contracts/effect_node_bypass.validation.yaml`` names the key,
the revision and the texts. A count only means something over the whole tree, so the hook hands the
validator the repository root, never a list of staged files.

Usage (pre-commit hook ``no-effect-node-bypass``)::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_effect_node_bypass:ValidatorEffectNodeBypass --baseline config/effect_node_bypass_ratchet.yaml .
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import ClassVar, Self

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.validation.checker_detector_common import parse_baseline
from omnibase_core.validation.checker_effect_node_bypass import (
    RULE_COUNT_RATCHET,
    check_count_ratchet,
    check_effect_node_bypass,
)
from omnibase_core.validation.checker_rule_parameters import rule_string
from omnibase_core.validation.validator_base import ValidatorBase
from omnibase_core.validators.no_unguarded_git_subprocess import scrub_git_location_env

__all__ = ["ValidatorEffectNodeBypass"]


class ValidatorEffectNodeBypass(ValidatorBase):
    """Read the tree, count the bypasses, and hold the count to the repository's count file."""

    validator_id: ClassVar[str] = "effect_node_bypass"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        root: Path | None = None,
        ratchet: int | None = None,
        ratchet_path: Path | None = None,
        base_ref: str | None = None,
    ) -> None:
        super().__init__(contract)
        self._root = (root or Path.cwd()).resolve()
        self._ratchet = ratchet
        self._ratchet_path = ratchet_path or Path()
        self._base_ref_override = base_ref
        self._rules = {r.rule_id: r for r in self.contract.rules}
        # an enabled row with a missing or mistyped parameter raises here, at load
        check_effect_node_bypass(Path("probe"), "", self._rules)

    @classmethod
    def with_baseline_file(cls, path: Path, *, base_ref: str | None = None) -> Self:
        """The validator held to the count file ``path`` (the hook's ``--baseline``).

        ``base_ref`` is the caller's base branch for the comparison with the base revision; with none, the
        contract's ``base_ref_fallback`` (the checkout's own ``HEAD``) is used and an unreadable base skips it.
        """
        probe = cls()
        key = rule_string(probe._rules[RULE_COUNT_RATCHET], "count_key")
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read the count file: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        count = parse_baseline(text).get(key)
        if count is None or count < 0:
            raise ModelOnexError(
                message=f"{path}: the count file holds no non-negative integer under {key!r}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        resolved = path.resolve()
        shown = (
            resolved.relative_to(probe._root)
            if resolved.is_relative_to(probe._root)
            else path
        )
        return cls(ratchet=count, ratchet_path=shown, base_ref=base_ref)

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ()
        resolved = path.resolve()
        shown = (
            resolved.relative_to(self._root)
            if resolved.is_relative_to(self._root)
            else path
        )
        rules = {r.rule_id: r for r in contract.rules}
        return check_effect_node_bypass(shown, source, rules)

    def validate(self, targets: Path | list[Path]) -> ModelValidationResult[None]:
        """Every finding of the run; held to the count file when one was given."""
        result = super().validate(targets)
        if self._ratchet is None:
            return result
        row = self._rules[RULE_COUNT_RATCHET]
        base_ref = self._base_ref_override or rule_string(row, "base_ref_fallback")
        base_ratchet, unreadable = self._base_ratchet(base_ref)
        issues: tuple[ModelValidationIssue, ...]
        # Only a base the caller named is refused when unreadable; the fallback (the checkout's own HEAD)
        # being unreadable means there is no git history to compare with, which is no base to hold.
        if unreadable is not None and self._base_ref_override is not None:
            issues = (
                ModelValidationIssue(
                    severity=row.severity,
                    message=rule_string(row, "base_unreadable_message").format(
                        path=self._ratchet_path.as_posix(),
                        base_ref=base_ref,
                        why=unreadable,
                    ),
                    code=row.rule_id,
                    file_path=self._ratchet_path,
                    line_number=1,
                    rule_name=row.rule_id,
                ),
            )
        else:
            issues = check_count_ratchet(
                len(result.issues),
                self._ratchet,
                None if unreadable is not None else base_ratchet,
                self._ratchet_path,
                self._rules,
            )
        if not issues:
            return result.model_copy(
                update={
                    "is_valid": True,
                    "issues": [],
                    "summary": (
                        f"Validation passed: {len(result.issues)} bypasses, "
                        f"count file {self._ratchet_path.as_posix()} holds {self._ratchet}"
                    ),
                }
            )
        return result.model_copy(
            update={
                "is_valid": False,
                "issues": [*issues, *result.issues],
                "summary": f"Validation failed: {len(issues)} count ratchet issue(s), "
                f"{len(result.issues)} bypass(es) found",
            }
        )

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", *args],
                cwd=self._root,
                env=scrub_git_location_env(),
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return subprocess.CompletedProcess(
                ["git", *args], 127, "", f"git did not run: {exc}"
            )

    def _base_ratchet(self, base_ref: str) -> tuple[int | None, str | None]:
        """The count file at the merge base of ``HEAD`` and ``base_ref``, and why it is unreadable.

        The count is ``None`` when the file is absent there (a count file new to this branch). Any git
        failure answers a reason instead, and the ratchet fails closed on it: on a CI checkout ``HEAD``
        is the judged commit, so the comparison is made with the merge base, and a base that cannot be
        read is a refusal, never a skipped check.
        """
        key = rule_string(self._rules[RULE_COUNT_RATCHET], "count_key")
        merge_base = self._git("merge-base", "HEAD", base_ref)
        if merge_base.returncode != 0 or not merge_base.stdout.strip():
            return None, merge_base.stderr.strip() or f"no merge base with {base_ref}"
        revision = merge_base.stdout.strip()
        location = self._ratchet_path.as_posix()
        listed = self._git("ls-tree", "--name-only", revision, "--", location)
        if listed.returncode != 0:
            return None, listed.stderr.strip() or "git ls-tree failed"
        if not listed.stdout.strip():
            return None, None
        shown = self._git("show", f"{revision}:{location}")
        if shown.returncode != 0:
            return None, shown.stderr.strip() or "git show failed"
        return parse_baseline(shown.stdout).get(key), None
