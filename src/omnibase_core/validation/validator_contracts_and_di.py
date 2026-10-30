# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorContractsAndDi -- refuse values and bindings that belong in contracts and DI (OMN-21623).

The ``ValidatorBase`` entry of the contracts-and-DI rules: it reads one file, works
out the file's repository and its repository-relative path, gathers the workspace pin
facts once per repository, and hands them with the contract's rule rows to the pure
``checker_contracts_and_di``. The scan set and every rule value live in
``contracts/contracts_and_di.validation.yaml``.

The pin facts come from the workspace the scanned repository sits in: by default the
directory that holds the repository's clone, or the ``workspace_roots`` a caller
injects when its clones live in more than one directory.

Usage::

    python -m omnibase_core.nodes.node_validation_report_write_effect.runtime_validator_run omnibase_core.validation.validator_contracts_and_di:ValidatorContractsAndDi <targets...>
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

import yaml

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.validation.model_contracts_and_di_facts import (
    ModelContractsAndDiFacts,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates
from omnibase_core.validation.checker_contracts_and_di import (
    check_contracts_and_di,
    pin_fact_parameters,
)
from omnibase_core.validation.validator_base import ValidatorBase

__all__ = ["ValidatorContractsAndDi"]


def _repository_root(path: Path) -> Path:
    """The nearest ancestor holding ``.git`` (a clone or a worktree), else the file's directory."""
    resolved = path.resolve()
    for candidate in resolved.parents:
        if (candidate / ".git").exists():
            return candidate
    return resolved.parent


def _manifest_sites(
    manifest_repository: str, document: object, keys: Sequence[str]
) -> set[str]:
    (
        repos_key,
        name_key,
        sites_key,
        site_path_key,
        dependency_key,
        pyproject_key,
        default_pyproject,
    ) = keys
    sites: set[str] = set()
    entries = document.get(repos_key) if isinstance(document, dict) else None
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get(name_key), str):
            continue
        consumer = entry[name_key]
        for site in entry.get(sites_key) or []:
            if isinstance(site, dict) and isinstance(site.get(site_path_key), str):
                sites.add(f"{manifest_repository}>{consumer}:{site[site_path_key]}")
        dependency = entry.get(dependency_key)
        if isinstance(dependency, dict):
            pyproject = dependency.get(pyproject_key) or default_pyproject
            sites.add(f"{manifest_repository}>{consumer}:{pyproject}")
    return sites


class ValidatorContractsAndDi(ValidatorBase):
    """Read one file and judge it against the contracts-and-DI rule rows."""

    validator_id: ClassVar[str] = "contracts_and_di"

    def __init__(
        self,
        contract: ModelValidatorSubcontract | None = None,
        *,
        workspace_roots: Sequence[Path] | None = None,
    ) -> None:
        super().__init__(contract)
        self._workspace_roots = (
            tuple(root.resolve() for root in workspace_roots)
            if workspace_roots is not None
            else None
        )
        self._facts: dict[Path, ModelContractsAndDiFacts] = {}

    def _facts_for(
        self, repository_root: Path, contract: ModelValidatorSubcontract
    ) -> ModelContractsAndDiFacts:
        cached = self._facts.get(repository_root)
        if cached is not None:
            return cached
        roots = self._workspace_roots or (repository_root.parent,)
        tag_sources: set[str] = set()
        sites: set[str] = set()
        for rule in contract.rules:
            if (
                not rule.enabled
                or (rule.parameters or {}).get("kind") != "first_party_pin"
            ):
                continue
            globs, manifests, keys = pin_fact_parameters(rule)
            for root in roots:
                for clone in sorted(p for p in root.iterdir() if p.is_dir()):
                    if any(next(clone.glob(glob), None) for glob in globs):
                        tag_sources.add(clone.name)
                for manifest in manifests:
                    repository, _, relative = manifest.partition(":")
                    manifest_path = root / repository / relative
                    if not manifest_path.is_file():
                        continue
                    try:
                        document = load_yaml_mapping_no_duplicates(
                            manifest_path.read_text(encoding="utf-8"),
                            source=str(manifest_path),
                        )
                    except (
                        OSError,
                        UnicodeDecodeError,
                        ValueError,
                        yaml.YAMLError,
                    ) as exc:
                        raise ModelOnexError(
                            message=f"{manifest_path}: cannot read advancer manifest: {exc}",
                            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        ) from exc
                    sites |= _manifest_sites(repository, document, keys)
        facts = ModelContractsAndDiFacts(
            repository=repository_root.name,
            tag_source_repositories=frozenset(tag_sources),
            advanced_sites=frozenset(sites),
        )
        self._facts[repository_root] = facts
        return facts

    def _validate_file(
        self,
        path: Path,
        contract: ModelValidatorSubcontract,
    ) -> tuple[ModelValidationIssue, ...]:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ModelOnexError(
                message=f"{path}: cannot read: {exc}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from exc
        root = _repository_root(path)
        relative = path.resolve().relative_to(root)
        issues = check_contracts_and_di(
            relative, text, contract.rules, self._facts_for(root, contract)
        )
        return tuple(i.model_copy(update={"file_path": path}) for i in issues)
