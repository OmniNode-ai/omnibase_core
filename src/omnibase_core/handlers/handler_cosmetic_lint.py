# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cosmetic lint of OmniNode repository standards (OMN-20074).

Ported from onex_change_control (``cosmetic-lint check``, pinned fleet rev
8d7e85bc00e7) for OCC retirement step S8. The decisions are the source's: SPDX
headers on Python files, ``pyproject.toml`` fields, pre-commit revisions,
README badges and ``.github`` templates and workflow extensions, each judged
against the spec carried byte for byte in ``contracts/cosmetic_lint_spec.yaml``.

The handler is pure over an explicit snapshot (:class:`ModelCosmeticLintInput`);
``main`` gathers that snapshot from the working directory through the
source-file gather EFFECT and prints one line per violation to stderr, in the
source's ``path:line: [check] message [fixable]`` form. Only ``check`` is ported:
the exported hook never ran ``fix``, and the best-effort Kafka score event of the
source (a no-op unless the optional ``kafka`` extra was installed) is not.

Usage::

    python -m omnibase_core.handlers.handler_cosmetic_lint [check]

Exit code 0 = clean. Exit code 1 = violations found, or a file unreadable.
Exit code 2 = unsupported arguments.
"""

from __future__ import annotations

import fnmatch
import importlib.resources
import sys
import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Final

from omnibase_core.errors.error_duplicate_yaml_mapping_key import (
    DuplicateYamlMappingKeyError,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_github_snapshot import (
    ModelCosmeticGithubSnapshot,
)
from omnibase_core.models.nodes.cosmetic_lint.model_cosmetic_lint_input import (
    ModelCosmeticLintInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.validation.model_validation_finding import (
    ModelValidationFinding,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationFindingEmbed,
    ModelValidationReport,
    ModelValidationRequestRef,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_mapping_no_duplicates

VALIDATOR_ID: Final[str] = "cosmetic-lint"
SPEC_RESOURCE: Final[str] = "cosmetic_lint_spec.yaml"
ALL_CHECKS: Final[tuple[str, ...]] = (
    "spdx",
    "pyproject",
    "precommit",
    "readme",
    "github",
)

_SKIP_MARKER: Final[str] = "spdx-skip"
_README_HEADER_LINES: Final[int] = 30
_USAGE_ERROR: Final[int] = 2


def load_spec_yaml() -> str:
    """Return the packaged cosmetic spec, byte for byte, as text."""
    ref = importlib.resources.files("omnibase_core.contracts") / SPEC_RESOURCE
    return ref.read_text(encoding="utf-8")


def _load_spec(spec_yaml: str) -> Mapping[str, object]:
    return _mapping(
        load_yaml_mapping_no_duplicates(spec_yaml, source="cosmetic lint spec")
    )


def _mapping(value: object) -> Mapping[str, object]:
    """The mapping *value* holds, or an empty one."""
    return value if isinstance(value, Mapping) else {}


def _mappings(value: object) -> list[Mapping[str, object]]:
    items = value if isinstance(value, list) else []
    return [item for item in items if isinstance(item, Mapping)]


def _strings(value: object, default: Sequence[str] = ()) -> list[str]:
    if not isinstance(value, list):
        return list(default)
    return [item for item in value if isinstance(item, str)]


def _text(value: object, default: str) -> str:
    return default if value is None else str(value)


def _violation(
    check: str, path: str, line: int, message: str, *, fixable: bool
) -> ModelValidationFindingEmbed:
    """One FAIL finding whose message is the source's output line."""
    tag = " [fixable]" if fixable else ""
    location = f"{path}:{line}"
    finding = ModelValidationFinding(
        validator_id=VALIDATOR_ID,
        severity="FAIL",
        rule_id=check,
        location=location,
        message=f"{location}: [{check}] {message}{tag}",
    )
    return ModelValidationFindingEmbed(**finding.model_dump(mode="json"))


# --- spdx -------------------------------------------------------------------


def _is_excluded(rel_path: str, exclude_patterns: list[str]) -> bool:
    """Check whether *rel_path* matches any exclude pattern."""
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(rel_path, pattern):
            return True
        if fnmatch.fnmatch("/" + rel_path, "/" + pattern.lstrip("*")):
            return True
        parts = pattern.replace("**", "").strip("/").split("/")
        parts = [p for p in parts if p and p != "*"]
        if parts:
            rel_parts = rel_path.replace("\\", "/").split("/")
            if all(component in rel_parts for component in parts):
                return True
    return False


def spdx_file_patterns(spec_yaml: str) -> list[str]:
    """Return the glob patterns of the files the SPDX check looks at."""
    spdx = _mapping(_load_spec(spec_yaml).get("spdx"))
    return _strings(spdx.get("file_patterns"), ["*.py"])


def select_python_paths(spec_yaml: str, paths: Sequence[str]) -> list[str]:
    """Return the *paths* the SPDX check judges, in the source's order.

    A path is judged when it matches a file pattern and no exclude pattern; the
    order is that of the source's ``sorted`` over ``Path`` objects, which
    compares path components, not the joined string.
    """
    spdx = _mapping(_load_spec(spec_yaml).get("spdx"))
    exclude_patterns = _strings(spdx.get("exclude_patterns"))
    matched: list[str] = []
    for pattern in spdx_file_patterns(spec_yaml):
        for rel in paths:
            if PurePosixPath(rel).match(pattern) and not _is_excluded(
                rel, exclude_patterns
            ):
                matched.append(rel)
    return sorted(matched, key=lambda rel: PurePosixPath(rel).parts)


def _check_spdx(
    request: ModelCosmeticLintInput, spec: Mapping[str, object]
) -> list[ModelValidationFindingEmbed]:
    spec_spdx = _mapping(spec.get("spdx"))
    sources = {f.path: f.source for f in request.python_files}
    copyright_line = f"# SPDX-FileCopyrightText: {spec_spdx['copyright_text']}"
    license_line = f"# SPDX-License-Identifier: {spec_spdx['license_identifier']}"
    findings: list[ModelValidationFindingEmbed] = []
    for rel in select_python_paths(request.spec_yaml, list(sources)):
        content = sources[rel]
        if _SKIP_MARKER in content:
            continue
        lines = content.splitlines()
        start = 1 if lines and lines[0].startswith("#!") else 0
        if len(lines) < start + 2:
            findings.append(
                _violation("spdx", rel, start + 1, "Missing SPDX header", fixable=True)
            )
            continue
        if lines[start] != copyright_line:
            findings.append(
                _violation(
                    "spdx",
                    rel,
                    start + 1,
                    f"Expected '{copyright_line}', got '{lines[start]}'",
                    fixable=True,
                )
            )
        if lines[start + 1] != license_line:
            findings.append(
                _violation(
                    "spdx",
                    rel,
                    start + 2,
                    f"Expected '{license_line}', got '{lines[start + 1]}'",
                    fixable=True,
                )
            )
    return findings


# --- pyproject --------------------------------------------------------------


def _pyproject_violation(message: str, *, fixable: bool) -> ModelValidationFindingEmbed:
    return _violation("pyproject", "pyproject.toml", 0, message, fixable=fixable)


_SpecSection = Mapping[str, object]


def _check_author(
    project: Mapping[str, object], spec_pyproject: _SpecSection
) -> list[ModelValidationFindingEmbed]:
    expected = _mapping(spec_pyproject["author"])
    if any(
        a.get("name") == expected["name"] and a.get("email") == expected["email"]
        for a in _mappings(project.get("authors"))
    ):
        return []
    return [
        _pyproject_violation(
            f'Expected author {{name = "{expected["name"]}", '
            f'email = "{expected["email"]}"}}',
            fixable=True,
        )
    ]


def _check_license(
    project: Mapping[str, object], spec_pyproject: _SpecSection
) -> list[ModelValidationFindingEmbed]:
    lic = project.get("license")
    expected_text = _text(spec_pyproject.get("license_text"), "MIT")
    expected_format = _text(spec_pyproject.get("license_format"), "table")
    if lic is None:
        return [_pyproject_violation("Missing license field", fixable=True)]
    if expected_format != "table":
        return []
    if isinstance(lic, str):
        return [
            _pyproject_violation(
                f"License should be table format "
                f'{{text = "{expected_text}"}}, got bare string "{lic}"',
                fixable=True,
            )
        ]
    if isinstance(lic, Mapping) and lic.get("text") != expected_text:
        return [
            _pyproject_violation(
                f'Expected license text "{expected_text}", got "{lic.get("text")}"',
                fixable=True,
            )
        ]
    return []


def _check_requires_python(
    project: Mapping[str, object], spec_pyproject: _SpecSection
) -> list[ModelValidationFindingEmbed]:
    expected = _text(spec_pyproject.get("requires_python"), ">=3.12")
    actual = project.get("requires-python", "")
    if actual == expected:
        return []
    return [
        _pyproject_violation(
            f'Expected requires-python "{expected}", got "{actual}"', fixable=True
        )
    ]


def _check_classifiers(
    project: Mapping[str, object], spec_pyproject: _SpecSection
) -> list[ModelValidationFindingEmbed]:
    actual = set(_strings(project.get("classifiers")))
    required = _strings(_mapping(spec_pyproject.get("classifiers")).get("required"))
    return [
        _pyproject_violation(f'Missing required classifier: "{c}"', fixable=True)
        for c in required
        if c not in actual
    ]


def _check_urls(
    project: Mapping[str, object], spec_pyproject: _SpecSection
) -> list[ModelValidationFindingEmbed]:
    urls = _mapping(project.get("urls"))
    required = _strings(_mapping(spec_pyproject.get("url_keys")).get("required"))
    return [
        _pyproject_violation(f'Missing required URL key: "{key}"', fixable=False)
        for key in required
        if key not in urls
    ]


def _check_ruff(
    data: Mapping[str, object], spec_pyproject: _SpecSection
) -> list[ModelValidationFindingEmbed]:
    ruff_spec = _mapping(spec_pyproject.get("ruff"))
    if not ruff_spec.get("required", False):
        return []
    ruff = _mapping(data.get("tool")).get("ruff")
    if ruff is None:
        return [_pyproject_violation("Missing [tool.ruff] section", fixable=False)]
    expected_target = _text(ruff_spec.get("target_version"), "py312")
    actual_target = _mapping(ruff).get("target-version", "")
    if actual_target == expected_target:
        return []
    return [
        _pyproject_violation(
            f'Expected ruff target-version "{expected_target}", got "{actual_target}"',
            fixable=False,
        )
    ]


def _check_pyproject(
    request: ModelCosmeticLintInput, spec: Mapping[str, object]
) -> list[ModelValidationFindingEmbed]:
    if request.pyproject_toml is None:
        return []
    data: Mapping[str, object] = tomllib.loads(request.pyproject_toml)
    project = _mapping(data.get("project"))
    spec_pyproject = _mapping(spec.get("pyproject"))
    return [
        *_check_author(project, spec_pyproject),
        *_check_license(project, spec_pyproject),
        *_check_requires_python(project, spec_pyproject),
        *_check_classifiers(project, spec_pyproject),
        *_check_urls(project, spec_pyproject),
        *_check_ruff(data, spec_pyproject),
    ]


# --- precommit --------------------------------------------------------------


def _config_mapping(config_text: str) -> Mapping[str, object]:
    """The pre-commit config as a mapping; an empty or non-mapping document reads as empty."""
    try:
        return _mapping(
            load_yaml_mapping_no_duplicates(
                config_text, source=".pre-commit-config.yaml"
            )
        )
    except ValueError as exc:
        if isinstance(exc, DuplicateYamlMappingKeyError):
            raise
        return {}


def _parse_versions(config_text: str) -> dict[str, str]:
    """Parse repo to rev mappings from the text of ``.pre-commit-config.yaml``."""
    data = _config_mapping(config_text)
    result: dict[str, str] = {}
    for repo in _mappings(data.get("repos")):
        url = repo.get("repo", "")
        rev = repo.get("rev", "")
        if url and rev and url != "local":
            result[str(url)] = str(rev)
    return result


def _check_precommit(
    request: ModelCosmeticLintInput, spec: Mapping[str, object]
) -> list[ModelValidationFindingEmbed]:
    if request.precommit_config is None:
        return []
    expected_versions = _mapping(_mapping(spec.get("precommit")).get("versions"))
    if not expected_versions:
        return []
    actual_versions = _parse_versions(request.precommit_config)
    findings: list[ModelValidationFindingEmbed] = []
    for repo_url, expected_rev in expected_versions.items():
        actual_rev = actual_versions.get(repo_url)
        if actual_rev is None or actual_rev == expected_rev:
            continue
        findings.append(
            _violation(
                "precommit",
                ".pre-commit-config.yaml",
                0,
                f"{repo_url}: expected rev {expected_rev}, got {actual_rev}",
                fixable=True,
            )
        )
    return findings


# --- readme -----------------------------------------------------------------


def _check_readme(
    request: ModelCosmeticLintInput, spec: Mapping[str, object]
) -> list[ModelValidationFindingEmbed]:
    if request.readme is None:
        return []
    lines = request.readme.splitlines()
    header_region = "\n".join(lines[:_README_HEADER_LINES]).lower()
    required_badges = _mappings(_mapping(spec.get("readme")).get("required_badges"))
    findings: list[ModelValidationFindingEmbed] = []
    for badge in required_badges:
        pattern = str(badge["pattern"]).lower()
        if pattern not in header_region:
            findings.append(
                _violation(
                    "readme",
                    "README.md",
                    0,
                    f"Missing required badge: {_text(badge.get('description'), pattern)}",
                    fixable=True,
                )
            )
    return findings


# --- github -----------------------------------------------------------------


def _check_github(
    request: ModelCosmeticLintInput, spec: Mapping[str, object]
) -> list[ModelValidationFindingEmbed]:
    snapshot = request.github
    if snapshot is None:
        return []
    spec_github = _mapping(spec.get("github"))
    entries = set(snapshot.entries)
    findings: list[ModelValidationFindingEmbed] = []
    for template in _strings(spec_github.get("required_templates")):
        if template not in entries:
            findings.append(
                _violation(
                    "github",
                    f".github/{template}",
                    0,
                    f"Missing required template: {template}",
                    fixable=False,
                )
            )
    expected_ext = _text(spec_github.get("workflow_extension"), ".yml")
    wrong_ext = ".yaml" if expected_ext == ".yml" else ".yml"
    workflows = sorted(
        entry.split("/", 1)[1]
        for entry in entries
        if entry.startswith("workflows/") and "/" not in entry.split("/", 1)[1]
    )
    for name in workflows:
        if PurePosixPath(name).suffix == wrong_ext:
            findings.append(
                _violation(
                    "github",
                    f".github/workflows/{name}",
                    0,
                    f"Workflow uses {wrong_ext} extension, expected {expected_ext}",
                    fixable=True,
                )
            )
    return findings


class HandlerCosmeticLint:
    """Decide, over an explicit repository snapshot, which standards it breaks."""

    def handle(self, request: ModelCosmeticLintInput) -> ModelValidationReport:
        """Return one FAIL finding per violation, in the source's check order."""
        spec = _load_spec(request.spec_yaml)
        findings: list[ModelValidationFindingEmbed] = [
            *_check_spdx(request, spec),
            *_check_pyproject(request, spec),
            *_check_precommit(request, spec),
            *_check_readme(request, spec),
            *_check_github(request, spec),
        ]
        return ModelValidationReport.from_findings(
            findings=tuple(findings),
            request=ModelValidationRequestRef(profile="default"),
            validators_run=(VALIDATOR_ID,),
        )


def _github_snapshot(root: Path) -> ModelCosmeticGithubSnapshot | None:
    github_dir = root / ".github"
    if not github_dir.is_dir():
        return None
    return ModelCosmeticGithubSnapshot(
        entries=sorted(
            p.relative_to(github_dir).as_posix()
            for p in github_dir.rglob("*")
            if p.exists()
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the exported hook on the working directory."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args not in ([], ["check"]):
        sys.stderr.write("usage: handler_cosmetic_lint [check]\n")
        return _USAGE_ERROR
    root = Path()
    spec_yaml = load_spec_yaml()
    candidates = [
        path.as_posix()
        for pattern in spdx_file_patterns(spec_yaml)
        for path in root.rglob(pattern)
        if path.is_file()
    ]
    named = [
        name
        for name in ("pyproject.toml", ".pre-commit-config.yaml", "README.md")
        if (root / name).exists()
    ]
    wanted = [*select_python_paths(spec_yaml, candidates), *named]
    # An empty explicit list would make the gather effect walk the whole tree.
    gathered = (
        NodeSourceFileGatherEffect().handle(
            ModelSourceFileGatherInput(
                root=".", explicit_paths=wanted, include_patterns=["**/*"]
            )
        )
        if wanted
        else None
    )
    if gathered is not None and gathered.skipped:
        for skipped in gathered.skipped:
            sys.stderr.write(f"ERROR: {skipped.path}: {skipped.reason}\n")
        return 1
    texts = {f.path: f.source for f in gathered.files} if gathered else {}
    report = HandlerCosmeticLint().handle(
        ModelCosmeticLintInput(
            spec_yaml=spec_yaml,
            python_files=[
                ModelSourceFile(path=path, source=source)
                for path, source in texts.items()
                if path not in named
            ],
            pyproject_toml=texts.get("pyproject.toml"),
            precommit_config=texts.get(".pre-commit-config.yaml"),
            readme=texts.get("README.md"),
            github=_github_snapshot(root),
        )
    )
    for finding in report.findings:
        sys.stderr.write(f"{finding.message}\n")
    return 1 if report.findings else 0


if __name__ == "__main__":
    sys.exit(main())
