# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Blocking generic validator for first-party references and sibling source pins."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, cast

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_first_party_ref_input import (
    ModelFirstPartyRefInput,
)
from omnibase_core.models.validation.model_first_party_tag_inventory_request import (
    ModelFirstPartyTagInventoryRequest,
)
from omnibase_core.models.validation.model_first_party_tag_inventory_result import (
    ModelFirstPartyTagInventoryResult,
)
from omnibase_core.models.validation.model_sibling_stale_parameters import (
    ModelSiblingStaleParameters,
)
from omnibase_core.validation.checker_first_party_ref import (
    check_first_party_refs,
    invalid,
    inventory_repositories,
    load_rule_parameters,
    matches,
)
from omnibase_core.validation.validator_base import ValidatorBase


class ValidatorFirstPartyRef(ValidatorBase):
    """Gather snapshots once so the pure checker can enforce cross-file invariants."""

    validator_id: ClassVar[str] = "first_party_ref"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        root: Path | None = None,
        inventory: Callable[
            [ModelFirstPartyTagInventoryRequest], ModelFirstPartyTagInventoryResult
        ]
        | None = None,
    ) -> None:
        super().__init__(contract)
        self.root = (Path.cwd() if root is None else root).resolve()
        self.inventory = inventory

    @property
    def contract(self) -> ModelValidatorSubcontract:
        contract = super().contract
        load_rule_parameters(contract)
        return contract

    def _load_contract(self) -> ModelValidatorSubcontract:
        contract = super()._load_contract()
        load_rule_parameters(contract)
        return contract

    def _gather(self, targets: Path | list[Path]) -> tuple[ModelSourceFile, ...]:
        paths: set[Path] = set()
        for target in [targets] if isinstance(targets, Path) else targets:
            if not target.exists():
                raise invalid(f"missing validation target: {target}")
            if target.is_dir():
                for pattern in self.contract.target_patterns:
                    paths.update(target.glob(pattern))
            else:
                paths.add(target)
        files: list[ModelSourceFile] = []
        for path in sorted(paths):
            if not path.is_file() or self._is_excluded(path):
                continue
            label = path.resolve().relative_to(self.root).as_posix()
            if matches(label, self.contract.target_patterns):
                files.append(
                    ModelSourceFile(path=label, source=path.read_text(encoding="utf-8"))
                )
        return tuple(files)

    def validate(self, targets: Path | list[Path]) -> ModelValidationResult[None]:
        files = self._gather(targets)
        requested = [targets] if isinstance(targets, Path) else targets
        if not files and any(target.is_dir() for target in requested):
            raise invalid("full-tree first_party_ref scan found no target files")
        facts = ModelFirstPartyRefInput(files=files)
        repositories = inventory_repositories(facts, self.contract)
        if repositories and self.inventory is None:
            raise invalid(
                "first_party_ref needs the tag inventory its runtime resolves from the container"
            )
        policy = cast(
            ModelSiblingStaleParameters,
            load_rule_parameters(self.contract)["stale_pin"],
        )
        inventories = (
            tuple(
                self.inventory(
                    ModelFirstPartyTagInventoryRequest(repo=repo, policy=policy)
                )
                for repo in repositories
            )
            if self.inventory is not None
            else ()
        )
        issues = check_first_party_refs(
            facts.model_copy(update={"dev_tags": inventories}), self.contract
        )
        return self._build_result(
            files_checked=[self.root / file.path for file in files],
            issues=list(issues),
            files_with_violations=sorted({str(i.file_path) for i in issues}),
            duration_ms=0,
        )

    def validate_file(self, path: Path) -> ModelValidationResult[None]:
        return self.validate([path])

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        return tuple(self.validate_file(path).issues)
