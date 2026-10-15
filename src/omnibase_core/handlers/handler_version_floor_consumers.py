# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""HandlerVersionFloorConsumers -- no floor raise ahead of consumers.

A pull request that raises the lower bound a repository declares on a sibling
registry distribution (one ``contracts/repo_layers.yaml`` lists) fails while
another registry repository that installs that distribution is not ready for
it. A consumer is not ready when:

* its own specifiers for the distribution exclude the new floor (an exact pin
  or an upper bound below it), so it cannot install the raising repository's
  next release at all; or
* it installs the raising repository's own distribution and the floor it
  declares for the sibling is below the new one (or it declares none).

A consumer's specifiers are every requirement it declares anywhere in
pyproject.toml: ``[project]`` dependencies and extras, ``[dependency-groups]``,
and ``[tool.uv]`` dev, override and constraint dependencies; its floor is the
highest lower bound among them.

This is the 2026-10-15 stall: omnimarket raised its omnibase-core floor to
0.47.44 while omnibase_infra pinned 0.47.39, and omnibase_infra's merge queue
failed until the consumer caught up. The order this check enforces is consumer
first, then the floor.

* FAIL -- a consumer that is not ready (it needs a PR raising its own pin or
  floor first), or that could not be read (never assumed compatible).
* ERROR -- the changed repository is not declared in the registry, or its
  pyproject does not parse.

Pure: no filesystem, no clock, no global state. Ticket: OMN-19998.
"""

from __future__ import annotations

import re
import tomllib
from typing import Final, Literal

from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.models.version_drift.model_declared_floor import (
    ModelDeclaredFloor,
)
from omnibase_core.models.version_drift.model_version_floor_check_input import (
    ModelVersionFloorCheckInput,
)

__all__ = [
    "VALIDATOR_ID",
    "admits",
    "HandlerVersionFloorConsumers",
    "declared_floors",
    "normalize_name",
    "parse_version",
]

VALIDATOR_ID: Final[str] = "version_floor_consumers"
_PROFILE: Final[Literal["strict", "default", "advisory"]] = "default"
_REMEDIATION: Final[str] = (
    "Raise the floor in every consumer named here first (land those pull requests), "
    "then raise it at the source. Never raise a floor ahead of its consumers."
)

_NAME = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(.*)$")
_CLAUSE = re.compile(r"^\s*(===|==|~=|>=|<=|!=|>|<)\s*([^\s,]+)\s*$")
_LOWER_OPS: Final[frozenset[str]] = frozenset({"===", "==", "~=", ">=", ">"})
_UPPER_OPS: Final[frozenset[str]] = frozenset({"===", "==", "~=", "<=", "<"})


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


def _lower_bound(specifier: str) -> tuple[int, ...] | None:
    """The lower bound one specifier string sets, or None when it sets none."""
    bound: tuple[int, ...] | None = None
    for clause in specifier.split(","):
        match = _CLAUSE.match(clause)
        if match is None or match.group(1) not in _LOWER_OPS:
            continue
        version = parse_version(match.group(2).removesuffix(".*"))
        if version and (bound is None or version > bound):
            bound = version
    return bound


def _admits(specifier: str, version: tuple[int, ...]) -> bool:
    """False when an exact pin or upper bound in ``specifier`` excludes ``version``."""
    for clause in specifier.split(","):
        match = _CLAUSE.match(clause)
        if match is None or match.group(1) not in _UPPER_OPS:
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


def admits(declared: ModelDeclaredFloor, version: tuple[int, ...]) -> bool:
    """True when no exact pin or upper bound ``declared`` holds excludes ``version``."""
    return all(_admits(bound, version) for bound in declared.bounds)


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


def declared_floors(pyproject: str) -> dict[str, ModelDeclaredFloor]:
    """Every distribution a pyproject declares, with its highest lower bound.

    Raises:
        tomllib.TOMLDecodeError: the text is not TOML.
    """
    floors: dict[str, ModelDeclaredFloor] = {}
    for requirement in _requirement_strings(tomllib.loads(pyproject)):
        match = _NAME.match(requirement)
        if match is None:
            continue
        name = normalize_name(match.group(1))
        rest = match.group(2).split(";", 1)[0].strip()
        specifier = "" if rest.startswith("@") else rest.strip("()")
        bound = _lower_bound(specifier)
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


class HandlerVersionFloorConsumers:
    """COMPUTE handler that refuses a floor raise ahead of registry consumers."""

    def handle(self, request: ModelVersionFloorCheckInput) -> ModelValidationReport:
        """Definition-B canonical entry-point: typed request in, typed report out."""
        own = request.layer_map.get(request.repo)
        if own is None:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID,
                (
                    f"repository {request.repo!r} is not declared in the registry; "
                    "declare it in contracts/repo_layers.yaml",
                ),
            )
        try:
            head = declared_floors(request.head_pyproject)
            base = (
                declared_floors(request.base_pyproject)
                if request.base_pyproject is not None
                else {}
            )
        except tomllib.TOMLDecodeError as exc:
            return ModelValidationReport.from_runtime_errors(
                VALIDATOR_ID, (f"{request.repo} pyproject.toml does not parse: {exc}",)
            )

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

        findings: list[ModelValidationFindingEmbed] = []
        for dist, new, old in raises:
            for consumer in sorted(request.consumers, key=lambda c: c.repo):
                if consumer.repo in (request.repo, owners[dist]):
                    continue
                problem = self._consumer_problem(
                    consumer.pyproject, dist, new, own_dists
                )
                if problem is None:
                    continue
                findings.append(
                    ModelValidationFindingEmbed(
                        validator_id=VALIDATOR_ID,
                        severity="FAIL",
                        location=f"{request.repo}/pyproject.toml",
                        message=(
                            f"{consumer.repo}: {request.repo} raises its {dist} floor "
                            f"{_show(old)} -> {_show(new)}, but {consumer.repo} at "
                            f"{consumer.ref} {problem}; a pull request to "
                            f"{consumer.repo} declaring {dist}>={_show(new)} must "
                            "land first"
                        ),
                        remediation=_REMEDIATION,
                    )
                )

        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile=_PROFILE),
            validators_run=(VALIDATOR_ID,),
        )

    @staticmethod
    def _consumer_problem(
        pyproject: str | None,
        dist: str,
        new: tuple[int, ...],
        raising_dists: set[str],
    ) -> str | None:
        """Why a consumer blocks the raise, or None when it does not."""
        if pyproject is None:
            return "could not be read, so it is never assumed compatible"
        try:
            floors = declared_floors(pyproject)
        except tomllib.TOMLDecodeError:
            return "has a pyproject.toml that does not parse"
        declared = floors.get(dist)
        if declared is None:
            return None
        listed = "; ".join(declared.specifiers)
        if not admits(declared, new):
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
