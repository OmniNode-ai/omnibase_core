# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorBase entry for contract-driven dev-merge tag verification."""

from __future__ import annotations

from collections.abc import Callable
from fnmatch import fnmatchcase
from pathlib import Path
from typing import ClassVar

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_dev_tag_lineage_facts import (
    ModelDevTagLineageFacts,
)
from omnibase_core.models.validation.model_dev_tag_lineage_request import (
    ModelDevTagLineageRequest,
)
from omnibase_core.validation.checker_dev_tag_lineage import (
    check_dev_tag_invariants,
    check_dev_tag_lineage,
    invalid,
    load_policy,
    parse_candidates,
    parse_lock,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorDevTagLineage(ValidatorBase):
    """Gather pyproject and adjacent lock text; inject all remote evidence."""

    validator_id: ClassVar[str] = "dev_tag_lineage"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        root: Path | None = None,
        resolver: Callable[[ModelDevTagLineageRequest], ModelDevTagLineageFacts]
        | None = None,
        package: str | None = None,
        rules: tuple[str, ...] | None = None,
    ) -> None:
        super().__init__(contract)
        self.root = (root or Path.cwd()).resolve()
        self.resolver = resolver
        self.package = package
        self.rules = rules

    def _selected_rule_ids(self, contract: ModelValidatorSubcontract) -> set[str]:
        """Resolve selection against the contract, refusing every unknown rule id."""
        available = {rule.rule_id for rule in contract.rules}
        if self.rules is None:
            return available
        selected = set(self.rules)
        unknown = selected - available
        if unknown:
            raise invalid(
                f"dev_tag_lineage unknown rule id(s): {', '.join(sorted(unknown))}"
            )
        return selected

    def validate(self, targets: Path | list[Path]) -> ModelValidationResult[None]:
        """Refuse missing inputs and gather each matching pyproject exactly once."""
        policy = load_policy(self.contract)
        self._selected_rule_ids(self.contract)
        requested = [targets] if isinstance(targets, Path) else targets
        requested = [
            target.with_name(policy.project_name)
            if target.name == policy.lock_name
            else target
            for target in requested
        ]
        for target in requested:
            if not target.exists():
                raise invalid(f"missing validation target: {target}")
        paths = [
            path
            for path in self._resolve_targets(requested)
            if not self._is_excluded(path)
            and any(
                fnmatchcase(path.name, pattern) or fnmatchcase(path.as_posix(), pattern)
                for pattern in self.contract.target_patterns
            )
        ]
        issues = [
            issue
            for path in paths
            for issue in self._validate_file(path, self.contract)
        ]
        return self._build_result(
            files_checked=paths,
            issues=issues,
            files_with_violations=sorted({str(issue.file_path) for issue in issues}),
            duration_ms=0,
        )

    def validate_file(self, path: Path) -> ModelValidationResult[None]:
        """Use the same fail-closed path as a tree scan."""
        return self.validate([path])

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        policy = load_policy(contract)
        selected = self._selected_rule_ids(contract)
        phases = {
            str((rule.parameters or {})["phase"])
            for rule in contract.rules
            if rule.rule_id in selected
        }
        text = path.read_text(encoding="utf-8")
        issues = (
            list(check_dev_tag_invariants(path, text, contract, self.package))
            if "invariant" in phases
            else []
        )
        candidates = (
            parse_candidates(text, policy, self.package) if "identity" in phases else ()
        )
        if candidates and self.resolver is None:
            raise invalid(
                "dev_tag_lineage needs the resolver its runtime resolves from the container"
            )
        if candidates:
            lock_path = path.with_name(policy.lock_name)
            entries = (
                parse_lock(lock_path.read_text(encoding="utf-8"), policy)
                if lock_path.exists()
                else None
            )
            for candidate in candidates:
                if self.resolver is None:
                    raise invalid("dev_tag_lineage resolver is missing")
                facts = self.resolver(
                    ModelDevTagLineageRequest(
                        url=candidate.url,
                        tag=candidate.tag,
                        branch=policy.branch,
                        policy=policy,
                    )
                )
                issues.extend(
                    check_dev_tag_lineage(path, candidate, facts, entries, contract)
                )
        return tuple(issue for issue in issues if issue.rule_name in selected)
