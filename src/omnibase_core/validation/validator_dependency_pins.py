# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorDependencyPins -- cross-repository dependency-pin entry (OMN-22360).

``ValidatorBase`` entry over :mod:`omnibase_core.validation.checker_dependency_pins`.
Handing it a repository's ``pyproject.toml``, ``uv.lock`` or ``.pre-commit-config.yaml``
(or the repository directory) judges that repository once. The two overlays are the
declared layer order (``contracts/repo_layers.yaml``) and the pin policy
(``contracts/dependency_pin_policy.yaml``); a caller passes either as a model (in
memory) or a file path, and the shipped copies are used otherwise. The release tags
and the hook history are read through the injected ``facts`` callable, so a test
hands in fixed facts and the runtime hands in the git effect.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from importlib import resources
from pathlib import Path
from typing import ClassVar

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_request import (
    ModelDependencyPinFactsRequest,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_facts_result import (
    ModelDependencyPinFactsResult,
)
from omnibase_core.models.dependency_pins.model_dependency_pin_policy import (
    ModelDependencyPinPolicy,
)
from omnibase_core.models.dependency_pins.model_dependency_pins_input import (
    ModelDependencyPinsInput,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model
from omnibase_core.validation.checker_dependency_pins import (
    RULE_FACTS,
    RULE_UNREADABLE,
    bounded_hook_pins,
    check_dependency_pins,
    dependency_repos,
    validate_rules,
)
from omnibase_core.validation.checker_rule_parameters import rule_int, rule_string
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = [
    "ValidatorDependencyPins",
    "load_dependency_pin_policy",
    "load_layer_order",
]

FactsReader = Callable[[ModelDependencyPinFactsRequest], ModelDependencyPinFactsResult]


def load_dependency_pin_policy(path: Path | None = None) -> ModelDependencyPinPolicy:
    """The pin policy overlay from ``path``, or the copy shipped inside the package."""
    text = (
        path.read_text("utf-8")
        if path is not None
        else resources.files("omnibase_core")
        .joinpath("contracts/dependency_pin_policy.yaml")
        .read_text("utf-8")
    )
    return load_yaml_content_as_model(text, ModelDependencyPinPolicy)


def load_layer_order(path: Path | None = None) -> ModelRepoLayerMap:
    """The layer order overlay from ``path``, or the copy shipped inside the package."""
    text = (
        path.read_text("utf-8")
        if path is not None
        else resources.files("omnibase_core")
        .joinpath("contracts/repo_layers.yaml")
        .read_text("utf-8")
    )
    return load_yaml_content_as_model(text, ModelRepoLayerMap)


def _shown(path: Path) -> str:
    """``path`` relative to the working directory when it is under it."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path)


class ValidatorDependencyPins(ValidatorBase):
    """Read one repository's manifests, gather facts through ``facts``, call the checker."""

    validator_id: ClassVar[str] = "dependency_pins"

    def __init__(
        self,
        facts: FactsReader,
        contract: ModelValidatorSubcontract | None = None,
        *,
        layer_order: ModelRepoLayerMap | None = None,
        policy: ModelDependencyPinPolicy | None = None,
        repo: str | None = None,
        hook_history_dir: str | None = None,
        today: date | None = None,
    ) -> None:
        super().__init__(contract)
        rules = {r.rule_id: r for r in self.contract.rules}
        validate_rules(rules)
        self._facts = facts
        self._layer_order = layer_order or load_layer_order()
        self._policy = policy or load_dependency_pin_policy()
        self._repo = repo
        self._hook_history_dir = hook_history_dir
        self._today = today

    def manifests(self, targets: list[Path]) -> list[Path]:
        """The repository manifests the targets name; empty when none."""
        return self._resolve_targets(targets)

    def _resolve_targets(self, targets: list[Path]) -> list[Path]:
        rules = {r.rule_id: r for r in self.contract.rules}
        lock = rule_string(rules[RULE_UNREADABLE], "lock_file_name")
        precommit = rule_string(rules[RULE_UNREADABLE], "precommit_file_name")
        name = rule_string(rules[RULE_UNREADABLE], "manifest_file_name")
        manifests: list[Path] = []
        for target in targets:
            if not target.exists():
                continue
            if target.is_dir():
                root = target
            elif target.name in (lock, precommit, name):
                root = target.parent
            else:
                continue
            manifest = (root / name).resolve()
            if (
                manifest.is_file()
                and manifest not in manifests
                and not self._is_excluded(manifest)
            ):
                manifests.append(manifest)
        return manifests

    def _validate_file(
        self, path: Path, contract: ModelValidatorSubcontract
    ) -> tuple[ModelValidationIssue, ...]:
        rules = {r.rule_id: r for r in contract.rules}
        unreadable = rules[RULE_UNREADABLE]
        lock_path = path.parent / rule_string(unreadable, "lock_file_name")
        precommit_path = path.parent / rule_string(unreadable, "precommit_file_name")
        request = ModelDependencyPinsInput(
            manifest_path=_shown(path),
            manifest_text=path.read_text(encoding="utf-8"),
            lock_path=_shown(lock_path),
            lock_text=lock_path.read_text(encoding="utf-8")
            if lock_path.is_file()
            else None,
            precommit_path=_shown(precommit_path),
            precommit_text=precommit_path.read_text(encoding="utf-8")
            if precommit_path.is_file()
            else None,
            repo=self._repo,
            layer_map=self._layer_order,
            policy=self._policy,
            checked_on=self._today or datetime.now(UTC).date(),
        )
        try:
            repos = dependency_repos(request, rules)
        except ModelOnexError:
            repos = ()
        try:
            pins = bounded_hook_pins(request.precommit_text, self._policy)
        except ModelOnexError:
            pins = ()
        facts = self._facts(
            ModelDependencyPinFactsRequest(
                github_org=self._layer_order.github_org,
                repos=repos,
                hook_pins=pins,
                policy=self._policy,
                hook_history_dir=self._hook_history_dir,
                git_timeout_seconds=rule_int(rules[RULE_FACTS], "git_timeout_seconds"),
            )
        )
        return check_dependency_pins(
            request.model_copy(
                update={
                    "inventories": facts.inventories,
                    "hook_histories": facts.hook_histories,
                }
            ),
            rules,
        )
