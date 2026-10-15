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

_INSTALL_OR_FETCH: Final[re.Pattern[str]] = re.compile(
    r"\b(?:pip3?\s+install|uv\s+pip\s+install|uv\s+add|uv\s+tool\s+install|uvx"
    r"|git\s+clone|gh\s+repo\s+clone|curl|wget)\b|git\+https?://",
    re.IGNORECASE,
)
_REPOSITORY: Final[re.Pattern[str]] = re.compile(
    r"^\s*-?\s*repository:\s*['\"]?([^\s'\"#]+)"
)
_REQUIREMENT_NAME: Final[re.Pattern[str]] = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)"
)

_SCRIPT_SUFFIXES: Final[tuple[str, ...]] = (".sh", ".bash", ".zsh", ".mk")


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def classify_path(path: str) -> EnumDependencyChannel | None:
    """The line-scanning channel a file belongs to, or None when it has none.

    ``.py`` files are scanned for imports and, when classified ``script`` here,
    also for install/fetch lines; ``pyproject.toml`` is parsed separately.
    """
    name = path.rsplit("/", 1)[-1]
    lowered = name.lower()
    if path.startswith(".github/") and lowered.endswith((".yml", ".yaml")):
        return EnumDependencyChannel.WORKFLOW
    if lowered.startswith(("dockerfile", "containerfile")) or lowered.endswith(
        ".dockerfile"
    ):
        return EnumDependencyChannel.DOCKERFILE
    if lowered.startswith(("requirements", "constraints")) and lowered.endswith(
        (".txt", ".in")
    ):
        return EnumDependencyChannel.REQUIREMENTS
    if lowered.endswith(_SCRIPT_SUFFIXES) or name in ("Makefile", "GNUmakefile"):
        return EnumDependencyChannel.SCRIPT
    if lowered.endswith(".py"):
        parts = path.split("/")[:-1]
        if "scripts" in parts and "tests" not in parts and "fixtures" not in parts:
            return EnumDependencyChannel.SCRIPT
    return None


def is_candidate(path: str) -> bool:
    """Whether ``path`` can carry a cross-repository reference this check reads."""
    return (
        path.endswith(".py")
        or path.rsplit("/", 1)[-1] == "pyproject.toml"
        or classify_path(path) is not None
    )


class _Names:
    """Lookup tables from a name to the repository that owns it."""

    def __init__(self, layer_map: ModelRepoLayerMap, own_repo: str) -> None:
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
                self.dists[_norm(dist)] = entry.repo
            self.slugs[entry.repo.lower()] = entry.repo
        tokens = sorted(
            {*self.modules, *(d for d in self.dists), *self.slugs},
            key=len,
            reverse=True,
        )
        self.token_re = (
            re.compile(
                r"(?<![A-Za-z0-9_.-])("
                + "|".join(re.escape(t).replace(r"\-", "[-_]") for t in tokens)
                + r")(?![A-Za-z0-9_-])"
            )
            if tokens
            else None
        )
        self.slug_re = re.compile(
            re.escape(layer_map.github_org)
            + r"/([A-Za-z0-9_.-]+?)(?:\.git)?(?=[/@\s'\"#]|$)",
            re.IGNORECASE,
        )

    def repo_for_token(self, token: str) -> str | None:
        lowered = token.lower()
        if lowered in self.modules:
            return self.modules[lowered]
        if _norm(lowered) in self.dists:
            return self.dists[_norm(lowered)]
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


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _install_fetch_refs(
    source: str, channel: EnumDependencyChannel, names: _Names
) -> Iterator[Reference]:
    for line_no, line in _logical_lines(source):
        if _is_comment(line) or not _INSTALL_OR_FETCH.search(line):
            continue
        for repo in sorted(names.repos_in(line)):
            yield channel, repo, line_no, line.strip()[:200]


def _workflow_refs(source: str, names: _Names) -> Iterator[Reference]:
    for line_no, line in enumerate(source.splitlines(), start=1):
        if _is_comment(line):
            continue
        match = _REPOSITORY.match(line)
        if match is None:
            continue
        slug = names.slug_re.match(match.group(1))
        repo = names.repo_for_slug(slug.group(1)) if slug else None
        if repo:
            yield EnumDependencyChannel.WORKFLOW, repo, line_no, line.strip()[:200]
    yield from _install_fetch_refs(source, EnumDependencyChannel.WORKFLOW, names)


def _requirements_refs(source: str, names: _Names) -> Iterator[Reference]:
    for line_no, line in enumerate(source.splitlines(), start=1):
        if _is_comment(line) or not line.strip():
            continue
        repos = names.repos_in(line) if "/" in line else set()
        match = _REQUIREMENT_NAME.match(line)
        if match:
            repo = names.dists.get(_norm(match.group(1)))
            if repo:
                repos.add(repo)
        for repo in sorted(repos):
            yield EnumDependencyChannel.REQUIREMENTS, repo, line_no, line.strip()[:200]


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
    try:
        document = tomllib.loads(source)
    except tomllib.TOMLDecodeError:
        return
    lines = source.splitlines()
    for table, requirement in _requirement_strings(document):
        match = _REQUIREMENT_NAME.match(requirement)
        repo = names.dists.get(_norm(match.group(1))) if match else None
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
    path: str, source: str, layer_map: ModelRepoLayerMap, own_repo: str
) -> list[Reference]:
    """Every reference from ``path`` to a repository other than ``own_repo``."""
    names = _Names(layer_map, own_repo)
    name = path.rsplit("/", 1)[-1]
    refs: list[Reference] = []
    if name == "pyproject.toml":
        refs.extend(_pyproject_refs(source, names))
        return refs
    channel = classify_path(path)
    if path.endswith(".py") and "fixtures" not in path.split("/")[:-1]:
        refs.extend(_import_refs(source, path, names))
    if channel is EnumDependencyChannel.WORKFLOW:
        refs.extend(_workflow_refs(source, names))
    elif channel is EnumDependencyChannel.REQUIREMENTS:
        refs.extend(_requirements_refs(source, names))
    elif channel is not None:
        refs.extend(_install_fetch_refs(source, channel, names))
    return refs
