# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure reference extraction for the dependency-direction check (OMN-19998).

Each function takes one file's repository-relative path and source text and
returns the cross-repository references it expresses, as
``(channel, target_repo, line, evidence)`` tuples. Nothing here reads the
filesystem; the runtime gathers files at the EFFECT boundary.

Channels and what counts as a reference:

* ``python_import`` -- ``import X`` / ``from X import`` where ``X``'s top-level
  name is another repository's declared Python module. Files under a
  ``fixtures`` directory are test data and are not read.
* ``pyproject`` -- a requirement in ``[project].dependencies``, any
  ``[project.optional-dependencies]`` extra, any ``[dependency-groups]`` group,
  ``[tool.uv].dev-dependencies``, ``[build-system].requires``, or a
  ``[tool.uv.sources]`` key, naming another repository's distribution.
* ``requirements`` -- a requirements or constraints line naming a distribution
  or ``<org>/<repo>``.
* ``dockerfile`` / ``script`` -- (a Python file only under a ``scripts``
  directory outside ``tests``) a logical line (backslash continuations
  joined) that installs, clones or fetches (``pip install``, ``uv pip install``,
  ``uv add``, ``uv tool install``, ``uvx``, ``git clone``, ``gh repo clone``,
  ``curl``, ``wget``, ``git+https``) and names a distribution, module or
  ``<org>/<repo>``.
* ``workflow`` -- under ``.github/``: ``repository: <org>/<repo>`` (a checkout
  of another repository's code, or a pin file naming one), plus install, clone
  and fetch lines as for scripts. ``uses: <org>/<repo>/...`` of a reusable
  workflow or action is CI inheritance, not a runtime dependency, and is not a
  reference.

Bare names (``omnimarket``, ``../omnimarket``) match case-sensitively, so prose
such as "Omnimarket:" in an echo line is not a reference; ``<org>/<repo>``
slugs match case-insensitively.
"""

from __future__ import annotations

import ast
import re
import tomllib
from collections.abc import Iterable, Iterator
from typing import Final

from omnibase_core.enums.enum_dependency_channel import EnumDependencyChannel
from omnibase_core.models.dependency_direction.model_dependency_direction_rules import (
    ModelDependencyDirectionRules,
)
from omnibase_core.models.dependency_direction.model_repo_layer_map import (
    ModelRepoLayerMap,
)

__all__ = [
    "VALIDATOR_ID",
    "Reference",
    "classify_path",
    "extract_references",
    "is_candidate",
]

VALIDATOR_ID: Final[str] = "dependency_direction"

# (channel, target repo, 1-based line, evidence text)
Reference = tuple[EnumDependencyChannel, str, int, str]


def _norm(name: str, rules: ModelDependencyDirectionRules) -> str:
    return re.sub(rules.name_separator_pattern, "-", name).lower()


def classify_path(
    path: str, rules: ModelDependencyDirectionRules
) -> EnumDependencyChannel | None:
    """The line-scanning channel a file belongs to, or None when it has none.

    ``.py`` files are scanned for imports and, when classified ``script`` here,
    also for install/fetch lines; ``pyproject.toml`` is parsed separately.
    """
    name = path.rsplit("/", 1)[-1]
    lowered = name.lower()
    if path.startswith(rules.workflow_dir_prefix) and lowered.endswith(
        rules.workflow_suffixes
    ):
        return EnumDependencyChannel.WORKFLOW
    if lowered.startswith(rules.dockerfile_prefixes) or lowered.endswith(
        rules.dockerfile_suffixes
    ):
        return EnumDependencyChannel.DOCKERFILE
    if lowered.startswith(rules.requirements_prefixes) and lowered.endswith(
        rules.requirements_suffixes
    ):
        return EnumDependencyChannel.REQUIREMENTS
    if lowered.endswith(rules.script_suffixes) or name in rules.makefile_names:
        return EnumDependencyChannel.SCRIPT
    if lowered.endswith(rules.python_suffix):
        parts = path.split("/")[:-1]
        if any(d in parts for d in rules.script_dirs) and not any(
            d in parts for d in rules.script_excluded_dirs
        ):
            return EnumDependencyChannel.SCRIPT
    return None


def is_candidate(path: str, rules: ModelDependencyDirectionRules) -> bool:
    """Whether ``path`` can carry a cross-repository reference this check reads."""
    return (
        path.endswith(rules.python_suffix)
        or path.rsplit("/", 1)[-1] == rules.pyproject_name
        or classify_path(path, rules) is not None
    )


class _Names:
    """Lookup tables from a name to the repository that owns it."""

    def __init__(
        self,
        layer_map: ModelRepoLayerMap,
        own_repo: str,
        rules: ModelDependencyDirectionRules,
    ) -> None:
        self.rules = rules
        self.org = layer_map.github_org.lower()
        self.modules: dict[str, str] = {}
        self.dists: dict[str, str] = {}
        self.slugs: dict[str, str] = {}
        for entry in layer_map.repos:
            if entry.repo == own_repo:
                continue
            for module in entry.python_modules:
                self.modules[module] = entry.repo
            for dist in entry.distributions:
                self.dists[_norm(dist, rules)] = entry.repo
            self.slugs[entry.repo.lower()] = entry.repo
        tokens = sorted(
            {*self.modules, *(d for d in self.dists), *self.slugs},
            key=len,
            reverse=True,
        )
        self.token_re = (
            re.compile(
                rules.token_before_pattern
                + "("
                + "|".join(re.escape(t).replace(r"\-", "[-_]") for t in tokens)
                + ")"
                + rules.token_after_pattern
            )
            if tokens
            else None
        )
        self.slug_re = re.compile(
            re.escape(layer_map.github_org) + rules.slug_repo_pattern,
            re.IGNORECASE,
        )

    def repo_for_token(self, token: str) -> str | None:
        lowered = token.lower()
        if lowered in self.modules:
            return self.modules[lowered]
        if _norm(lowered, self.rules) in self.dists:
            return self.dists[_norm(lowered, self.rules)]
        return self.slugs.get(lowered.replace("-", "_"), self.slugs.get(lowered))

    def repo_for_slug(self, slug_repo: str) -> str | None:
        return self.slugs.get(slug_repo.lower())

    def repos_in(self, text: str) -> set[str]:
        found: set[str] = set()
        for match in self.slug_re.finditer(text):
            repo = self.repo_for_slug(match.group(1))
            if repo:
                found.add(repo)
        if self.token_re is not None:
            for match in self.token_re.finditer(text):
                repo = self.repo_for_token(match.group(1))
                if repo:
                    found.add(repo)
        return found


def _logical_lines(source: str) -> Iterator[tuple[int, str]]:
    """Lines with backslash continuations joined; yields the first line number."""
    start = 0
    buffer: list[str] = []
    for index, raw in enumerate(source.splitlines(), start=1):
        if not buffer:
            start = index
        stripped = raw.rstrip()
        if stripped.endswith("\\"):
            buffer.append(stripped[:-1])
            continue
        buffer.append(stripped)
        yield start, " ".join(buffer)
        buffer = []
    if buffer:
        yield start, " ".join(buffer)


def _is_comment(line: str, rules: ModelDependencyDirectionRules) -> bool:
    return line.lstrip().startswith(rules.comment_prefix)


def _install_fetch_refs(
    source: str, channel: EnumDependencyChannel, names: _Names
) -> Iterator[Reference]:
    rules = names.rules
    install_or_fetch = re.compile(rules.install_or_fetch_pattern)
    for line_no, line in _logical_lines(source):
        if _is_comment(line, rules) or not install_or_fetch.search(line):
            continue
        for repo in sorted(names.repos_in(line)):
            yield channel, repo, line_no, line.strip()[: rules.evidence_limit]


def _workflow_refs(source: str, names: _Names) -> Iterator[Reference]:
    rules = names.rules
    repository = re.compile(rules.repository_pattern)
    for line_no, line in enumerate(source.splitlines(), start=1):
        if _is_comment(line, rules):
            continue
        match = repository.match(line)
        if match is None:
            continue
        slug = names.slug_re.match(match.group(1))
        repo = names.repo_for_slug(slug.group(1)) if slug else None
        if repo:
            yield (
                EnumDependencyChannel.WORKFLOW,
                repo,
                line_no,
                line.strip()[: rules.evidence_limit],
            )
    yield from _install_fetch_refs(source, EnumDependencyChannel.WORKFLOW, names)


def _requirements_refs(source: str, names: _Names) -> Iterator[Reference]:
    rules = names.rules
    requirement_name = re.compile(rules.requirement_name_pattern)
    for line_no, line in enumerate(source.splitlines(), start=1):
        if _is_comment(line, rules) or not line.strip():
            continue
        repos = names.repos_in(line) if "/" in line else set()
        match = requirement_name.match(line)
        if match:
            repo = names.dists.get(_norm(match.group(1), rules))
            if repo:
                repos.add(repo)
        for repo in sorted(repos):
            yield (
                EnumDependencyChannel.REQUIREMENTS,
                repo,
                line_no,
                line.strip()[: rules.evidence_limit],
            )


def _requirement_strings(document: dict[str, object]) -> Iterator[tuple[str, str]]:
    """(table, requirement) pairs from every dependency-bearing pyproject table."""

    def strings(value: object) -> Iterable[str]:
        if isinstance(value, list):
            return [v for v in value if isinstance(v, str)]
        return []

    project = document.get("project")
    if isinstance(project, dict):
        for req in strings(project.get("dependencies")):
            yield "project.dependencies", req
        extras = project.get("optional-dependencies")
        if isinstance(extras, dict):
            for extra, reqs in extras.items():
                for req in strings(reqs):
                    yield f"project.optional-dependencies.{extra}", req
    groups = document.get("dependency-groups")
    if isinstance(groups, dict):
        for group, reqs in groups.items():
            for req in strings(reqs):
                yield f"dependency-groups.{group}", req
    build = document.get("build-system")
    if isinstance(build, dict):
        for req in strings(build.get("requires")):
            yield "build-system.requires", req
    tool = document.get("tool")
    uv = tool.get("uv") if isinstance(tool, dict) else None
    if isinstance(uv, dict):
        for req in strings(uv.get("dev-dependencies")):
            yield "tool.uv.dev-dependencies", req
        sources = uv.get("sources")
        if isinstance(sources, dict):
            for name in sources:
                yield "tool.uv.sources", str(name)


def _pyproject_refs(source: str, names: _Names) -> Iterator[Reference]:
    rules = names.rules
    requirement_name = re.compile(rules.requirement_name_pattern)
    try:
        document = tomllib.loads(source)
    except tomllib.TOMLDecodeError:
        return
    lines = source.splitlines()
    for table, requirement in _requirement_strings(document):
        match = requirement_name.match(requirement)
        repo = names.dists.get(_norm(match.group(1), rules)) if match else None
        if repo is None:
            continue
        line_no = next(
            (i for i, text in enumerate(lines, start=1) if requirement in text), 0
        )
        yield EnumDependencyChannel.PYPROJECT, repo, line_no, f"{table}: {requirement}"


def _import_refs(source: str, path: str, names: _Names) -> Iterator[Reference]:
    try:
        tree = ast.parse(source, filename=path)
    except (SyntaxError, ValueError):
        return
    for node in ast.walk(tree):
        modules: list[str] = []
        line = 0
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
            line = node.lineno
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules = [node.module]
            line = node.lineno
        for module in modules:
            repo = names.modules.get(module.split(".", 1)[0])
            if repo:
                yield (
                    EnumDependencyChannel.PYTHON_IMPORT,
                    repo,
                    line,
                    f"import {module}",
                )


def extract_references(
    path: str,
    source: str,
    layer_map: ModelRepoLayerMap,
    own_repo: str,
    rules: ModelDependencyDirectionRules,
) -> list[Reference]:
    """Every reference from ``path`` to a repository other than ``own_repo``."""
    names = _Names(layer_map, own_repo, rules)
    name = path.rsplit("/", 1)[-1]
    refs: list[Reference] = []
    if name == rules.pyproject_name:
        refs.extend(_pyproject_refs(source, names))
        return refs
    channel = classify_path(path, rules)
    if path.endswith(rules.python_suffix) and not any(
        d in path.split("/")[:-1] for d in rules.fixture_dirs
    ):
        refs.extend(_import_refs(source, path, names))
    if channel is EnumDependencyChannel.WORKFLOW:
        refs.extend(_workflow_refs(source, names))
    elif channel is EnumDependencyChannel.REQUIREMENTS:
        refs.extend(_requirements_refs(source, names))
    elif channel is not None:
        refs.extend(_install_fetch_refs(source, channel, names))
    return refs
