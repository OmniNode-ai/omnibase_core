# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure venv build-lock checker: surfaces and locks in, issues out (OMN-22649).

A venv answers to the lock it was built from. The lock of a checkout that is being
committed has not built any venv yet, so judging a surface against it leaves a
lock-moving commit with no venv that can pass: the registry pins are read against one
lock and the git sources against another. This checker judges every surface against its
own build lock only, and states, as a non-failing issue, how far the checkout lock has
moved from that build lock. It performs no I/O. Severities and message texts are rule
rows of ``contracts/venv_build_lock.validation.yaml``.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.task_criteria.model_task_criteria_rule_row import (
    ModelTaskCriteriaRuleRow,
)
from omnibase_core.models.venv_build_lock.model_venv_build_lock_check_input import (
    ModelVenvBuildLockCheckInput,
)
from omnibase_core.models.venv_build_lock.model_venv_build_lock_check_result import (
    ModelVenvBuildLockCheckResult,
)
from omnibase_core.models.venv_build_lock.model_venv_build_lock_surface import (
    ModelVenvBuildLockSurface,
)

__all__ = ["build_lock_for", "check_venv_build_lock", "parse_lock"]


def _contract_error(message: str) -> ModelOnexError:
    return ModelOnexError(
        message=message, error_code=EnumCoreErrorCode.CONTRACT_VALIDATION_ERROR
    )


def _rows(contract: ModelValidatorSubcontract) -> dict[str, ModelTaskCriteriaRuleRow]:
    """Every rule of the contract as a row with its message and source pattern."""
    rows: dict[str, ModelTaskCriteriaRuleRow] = {}
    for rule in contract.rules:
        params = rule.parameters or {}
        texts = {
            name: value for name, value in params.items() if isinstance(value, str)
        }
        for name in ("message", "source_pattern"):
            if name not in texts:
                raise _contract_error(
                    f"{rule.rule_id}: required parameter {name} must be a string"
                )
        rows[rule.rule_id] = ModelTaskCriteriaRuleRow(
            enabled=rule.enabled,
            severity=rule.severity,
            message=texts.pop("message"),
            source_pattern=texts.pop("source_pattern"),
            texts=texts,
        )
    return rows


def _row(
    rows: dict[str, ModelTaskCriteriaRuleRow], rule_id: str
) -> ModelTaskCriteriaRuleRow:
    """The row of a rule the check needs; an absent rule is a contract error."""
    if rule_id not in rows:
        raise _contract_error(f"{rule_id}: required rule is absent")
    return rows[rule_id]


def _normalize(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def parse_lock(text: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return ``(registry versions, git commits)`` that a ``uv.lock`` text pins."""
    document = tomllib.loads(text)
    registry: dict[str, str] = {}
    git: dict[str, str] = {}
    for package in document.get("package", []):
        name = _normalize(str(package.get("name", "")))
        source = package.get("source", {})
        if not isinstance(source, dict) or not name:
            continue
        git_url = source.get("git")
        if isinstance(git_url, str):
            _, _, commit = git_url.partition("#")
            if commit:
                git[name] = commit
        elif "registry" in source and "version" in package:
            registry[name] = str(package["version"])
    return registry, git


def build_lock_for(
    surface: ModelVenvBuildLockSurface, checkout_lock_text: str
) -> str | None:
    """The lock text a surface is judged against: the lock it was built from.

    The checkout lock is a parameter only so a test can name the break that returns it
    (or another lock the surface was not built from) here.
    """
    del checkout_lock_text
    return surface.build_lock_text


def _commit_matches(installed: str, pinned: str, min_prefix: int) -> bool:
    short, long = sorted((installed, pinned), key=len)
    return len(short) >= min_prefix and long.startswith(short)


def _issue(
    row: ModelTaskCriteriaRuleRow,
    request: ModelVenvBuildLockCheckInput,
    code: str,
    context: Mapping[str, str],
) -> ModelValidationIssue | None:
    if not row.enabled or not row.judges(request.source_name):
        return None
    return ModelValidationIssue(
        severity=row.severity,
        message=row.message.format(**context),
        code=code,
        rule_name=code,
        context=dict(context),
    )


def check_venv_build_lock(
    request: ModelVenvBuildLockCheckInput,
) -> ModelVenvBuildLockCheckResult:
    """Judge each surface against the lock it was built from, never the checkout lock."""
    rows = _rows(request.contract)
    checkout_registry, checkout_git = parse_lock(request.checkout_lock_text)
    found: list[ModelValidationIssue | None] = []
    judged = 0
    for surface in request.surfaces:
        base = {"label": surface.label, "lock": surface.build_lock_path}
        lock_text = build_lock_for(surface, request.checkout_lock_text)
        if lock_text is None:
            found.append(
                _issue(
                    _row(rows, "build_lock_unreadable"),
                    request,
                    "build_lock_unreadable",
                    {**base, "name": "", "installed": "", "pinned": ""},
                )
            )
            continue
        registry, git = parse_lock(lock_text)
        min_prefix = int(_row(rows, "surface_git_pin").texts["min_commit_prefix"])
        judged += 1
        for name, version in sorted(surface.installed.items()):
            pinned = registry.get(_normalize(name))
            if pinned is not None and pinned != version:
                found.append(
                    _issue(
                        _row(rows, "surface_registry_pin"),
                        request,
                        "surface_registry_pin",
                        {**base, "name": name, "installed": version, "pinned": pinned},
                    )
                )
        for name, commit in sorted(surface.installed_git.items()):
            pinned = git.get(_normalize(name))
            if pinned is not None and not _commit_matches(commit, pinned, min_prefix):
                found.append(
                    _issue(
                        _row(rows, "surface_git_pin"),
                        request,
                        "surface_git_pin",
                        {**base, "name": name, "installed": commit, "pinned": pinned},
                    )
                )
        moved = sorted(
            {
                n
                for n in set(registry) | set(checkout_registry)
                if registry.get(n) != checkout_registry.get(n)
            }
            | {
                n
                for n in set(git) | set(checkout_git)
                if git.get(n) != checkout_git.get(n)
            }
        )
        if moved:
            found.append(
                _issue(
                    _row(rows, "checkout_lock_not_authority"),
                    request,
                    "checkout_lock_not_authority",
                    {
                        **base,
                        "name": ",".join(moved[:5]),
                        "installed": str(len(moved)),
                        "pinned": "",
                    },
                )
            )
    return ModelVenvBuildLockCheckResult(
        issues=tuple(i for i in found if i is not None), surfaces_judged=judged
    )
