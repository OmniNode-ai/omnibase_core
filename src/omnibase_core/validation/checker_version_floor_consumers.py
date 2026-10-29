# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure version-floor consumer checker (OMN-19998, OMN-21503).

Typed repository and consumer facts in, ModelValidationIssue out. Consumers
must accept a raised sibling floor before the raising repository lands it.
Patterns, operators, remediation and runtime error templates live in the rule
rows of contracts/version_floor_consumers.validation.yaml.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.version_drift.model_declared_floor import ModelDeclaredFloor
from omnibase_core.models.version_drift.model_version_floor_check_input import (
    ModelVersionFloorCheckInput,
)
from omnibase_core.validation.checker_rule_parameters import rule_string, rule_strings

RULE_FLOOR = "floor_raised_ahead_of_consumers"
RULE_REPO = "repo_not_in_registry"
RULE_UNPARSABLE = "pyproject_unparsable"


@lru_cache(maxsize=32)
def _re(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def normalize_name(name: str) -> str:
    """PEP 503 normalized distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_version(text: str) -> tuple[int, ...]:
    """The release segment of a version as an int tuple, trailing zeros dropped."""
    match = re.match(r"^\s*v?(\d+(?:\.\d+)*)", text)
    if match is None:
        return ()
    release = [int(part) for part in match.group(1).split(".")]
    while len(release) > 1 and release[-1] == 0:
        release.pop()
    return tuple(release)


def _lower_bound(specifier: str, row: ModelValidatorRule) -> tuple[int, ...] | None:
    """The lower bound one specifier string sets, or None when it sets none."""
    bound: tuple[int, ...] | None = None
    for clause in specifier.split(","):
        match = _re(rule_string(row, "clause_pattern")).match(clause)
        if match is None or match.group(1) not in rule_strings(row, "lower_operators"):
            continue
        version = parse_version(match.group(2).removesuffix(".*"))
        if version and (bound is None or version > bound):
            bound = version
    return bound


def _admits(specifier: str, version: tuple[int, ...], row: ModelValidatorRule) -> bool:
    """False when an exact pin or upper bound in ``specifier`` excludes ``version``."""
    for clause in specifier.split(","):
        match = _re(rule_string(row, "clause_pattern")).match(clause)
        if match is None or match.group(1) not in rule_strings(row, "upper_operators"):
            continue
        op, raw = match.groups()
        wildcard = raw.endswith(".*")
        bound = parse_version(raw.removesuffix(".*"))
        if not bound:
            continue
        if op in ("==", "===") and wildcard:
            if (version + (0,) * len(bound))[: len(bound)] != bound:
                return False
        elif op in ("==", "==="):
            if version != bound:
                return False
        elif op == "~=":
            release = [int(p) for p in raw.split(".") if p.isdigit()]
            if len(release) >= 2:
                ceiling = parse_version(
                    ".".join(str(p) for p in (*release[:-2], release[-2] + 1))
                )
                if version >= ceiling:
                    return False
        elif (op == "<" and version >= bound) or (op == "<=" and version > bound):
            return False
    return True


def admits(
    declared: ModelDeclaredFloor, version: tuple[int, ...], row: ModelValidatorRule
) -> bool:
    """True when no exact pin or upper bound ``declared`` holds excludes ``version``."""
    return all(_admits(bound, version, row) for bound in declared.bounds)


def _requirement_strings(data: dict[str, object]) -> list[str]:
    found: list[str] = []

    def take(value: object) -> None:
        if isinstance(value, list):
            found.extend(item for item in value if isinstance(item, str))

    project = data.get("project")
    if isinstance(project, dict):
        take(project.get("dependencies"))
        extras = project.get("optional-dependencies")
        if isinstance(extras, dict):
            for value in extras.values():
                take(value)
    groups = data.get("dependency-groups")
    if isinstance(groups, dict):
        for value in groups.values():
            take(value)
    tool = data.get("tool")
    uv = tool.get("uv") if isinstance(tool, dict) else None
    if isinstance(uv, dict):
        for key in (
            "dev-dependencies",
            "override-dependencies",
            "constraint-dependencies",
        ):
            take(uv.get(key))
    return found


def declared_floors(
    pyproject: str, row: ModelValidatorRule
) -> dict[str, ModelDeclaredFloor]:
    """Every distribution a pyproject declares, with its highest lower bound.

    Raises:
        tomllib.TOMLDecodeError: the text is not TOML.
    """
    floors: dict[str, ModelDeclaredFloor] = {}
    for requirement in _requirement_strings(tomllib.loads(pyproject)):
        match = _re(rule_string(row, "name_pattern")).match(requirement)
        if match is None:
            continue
        name = normalize_name(match.group(1))
        rest = match.group(2).split(";", 1)[0].strip()
        specifier = "" if rest.startswith("@") else rest.strip("()")
        bound = _lower_bound(specifier, row)
        previous = floors.get(name)
        if previous is None:
            floors[name] = ModelDeclaredFloor(
                floor=bound, specifiers=(requirement.strip(),), bounds=(specifier,)
            )
            continue
        best = previous.floor
        if bound is not None and (best is None or bound > best):
            best = bound
        floors[name] = ModelDeclaredFloor(
            floor=best,
            specifiers=(*previous.specifiers, requirement.strip()),
            bounds=(*previous.bounds, specifier),
        )
    return floors


def _show(version: tuple[int, ...] | None) -> str:
    return "none" if version is None else ".".join(str(part) for part in version)


def check_version_floor_consumers(
    request: ModelVersionFloorCheckInput,
    rules: Mapping[str, ModelValidatorRule],
) -> tuple[ModelValidationIssue, ...]:
    """Refuse floor raises while a registry consumer is not ready for them."""
    row = rules[RULE_FLOOR]
    # Validate the contract even when the input happens to have no floor raise.
    rule_string(row, "name_pattern")
    rule_string(row, "clause_pattern")
    rule_strings(row, "lower_operators")
    rule_strings(row, "upper_operators")
    rule_string(row, "remediation")
    rule_string(rules[RULE_REPO], "message_template")
    rule_string(rules[RULE_UNPARSABLE], "message_template")
    path = f"{request.repo}/pyproject.toml"
    own = request.layer_map.get(request.repo)
    if own is None:
        error_row = rules[RULE_REPO]
        return (
            (
                _issue(
                    error_row,
                    path,
                    rule_string(error_row, "message_template").format(
                        repo=request.repo
                    ),
                ),
            )
            if error_row.enabled
            else ()
        )
    try:
        head = declared_floors(request.head_pyproject, row)
        base = (
            declared_floors(request.base_pyproject, row)
            if request.base_pyproject is not None
            else {}
        )
    except tomllib.TOMLDecodeError as exc:
        error_row = rules[RULE_UNPARSABLE]
        return (
            (
                _issue(
                    error_row,
                    path,
                    rule_string(error_row, "message_template").format(
                        repo=request.repo, error=exc
                    ),
                ),
            )
            if error_row.enabled
            else ()
        )
    if not row.enabled:
        return ()
    owners = {
        normalize_name(dist): entry.repo
        for entry in request.layer_map.repos
        for dist in entry.distributions
    }
    own_dists = {normalize_name(d) for d in own.distributions}
    raises: list[tuple[str, tuple[int, ...], tuple[int, ...] | None]] = []
    for dist, declared in sorted(head.items()):
        if dist not in owners or dist in own_dists or declared.floor is None:
            continue
        before = base.get(dist)
        old = before.floor if before is not None else None
        if old is None or declared.floor > old:
            raises.append((dist, declared.floor, old))

    issues: list[ModelValidationIssue] = []
    for dist, new, old in raises:
        for consumer in sorted(request.consumers, key=lambda c: c.repo):
            if consumer.repo in (request.repo, owners[dist]):
                continue
            problem = _consumer_problem(consumer.pyproject, dist, new, own_dists, row)
            if problem is None:
                continue
            issues.append(
                _issue(
                    row,
                    path,
                    f"{consumer.repo}: {request.repo} raises its {dist} floor "
                    f"{_show(old)} -> {_show(new)}, but {consumer.repo} at "
                    f"{consumer.ref} {problem}; a pull request to "
                    f"{consumer.repo} declaring {dist}>={_show(new)} must "
                    "land first",
                )
            )
    return tuple(issues)


def _issue(row: ModelValidatorRule, path: str, message: str) -> ModelValidationIssue:
    return ModelValidationIssue(
        severity=row.severity,
        message=message,
        code=row.rule_id,
        file_path=Path(path),
        rule_name=row.rule_id,
        suggestion=rule_string(row, "remediation")
        if row.rule_id == RULE_FLOOR
        else None,
    )


def _consumer_problem(
    pyproject: str | None,
    dist: str,
    new: tuple[int, ...],
    raising_dists: set[str],
    row: ModelValidatorRule,
) -> str | None:
    """Why a consumer blocks the raise, or None when it does not."""
    if pyproject is None:
        return "could not be read, so it is never assumed compatible"
    try:
        floors = declared_floors(pyproject, row)
    except tomllib.TOMLDecodeError:
        return "has a pyproject.toml that does not parse"
    declared = floors.get(dist)
    if declared is None:
        return None
    listed = "; ".join(declared.specifiers)
    if not admits(declared, new, row):
        return f"pins {dist} below the new floor ({listed})"
    if not raising_dists.intersection(floors):
        return None
    if declared.floor is None:
        return f"installs the raising repository and declares {dist} with no lower bound ({listed})"
    if declared.floor < new:
        return (
            "installs the raising repository and declares a floor of "
            f"{_show(declared.floor)} ({listed})"
        )
    return None
