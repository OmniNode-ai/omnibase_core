# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ValidatorBannedComposeVars — kernel-sourced banned env var detector.

Scans every ``docker-compose*.yaml`` and every ``k8s/**/*.yaml`` for
``environment:`` / ``env:`` blocks and flags any entry whose NAME appears in
the kernel's ``_DEPRECATED_TOPIC_ENV_VARS`` constant (canonical source of
truth for topic env vars that code no longer reads).

**Ground truth**: ``omnibase_infra/src/omnibase_infra/runtime/service_kernel.py``
defines ``_DEPRECATED_TOPIC_ENV_VARS`` (OMN-8784). This validator parses that
file via ``ast`` to pull the current set — single source of truth, no
duplication.

The validator is layer-clean (omnibase_core cannot import omnibase_infra per
repo layering rules). Instead it reads the kernel source as a text file and
extracts the constant with a static AST walk.

Drift kind reported:

- **BANNED_VAR**: compose/k8s exposes an env var whose NAME is in the banned
  set (regardless of value). Stale compose — the OMN-8840 pattern where
  ``ONEX_INPUT_TOPIC`` survived after OMN-8784 removed it from code.

``MISSING_VAR`` (forward-drift contract→compose check — for each contract's
declared topics, verify a compose entry exposes the expected env var) is
deferred to follow-up ticket OMN-9064. The enum value is preserved.

Related ticket: OMN-9062 (trigger: OMN-8840, parent: OMN-9048).

Usage::

    # Programmatic
    from pathlib import Path
    from omnibase_core.validation import ValidatorBannedComposeVars

    validator = ValidatorBannedComposeVars(
        kernel_source_path=Path("../omnibase_infra/src/omnibase_infra/runtime/service_kernel.py"),
    )
    violations = validator.check_paths([Path("omni_home")])

    # CLI (per repo policy: all Python commands via uv run)
    uv run python -m omnibase_core.nodes.node_banned_compose_vars_check_compute.runtime_banned_compose_vars_check \\
        --kernel-source ../omnibase_infra/src/omnibase_infra/runtime/service_kernel.py \\
        omni_home/

Exit codes:
    0 — no drift
    2 — drift detected
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_compose_drift_kind import EnumComposeDriftKind
from omnibase_core.models.validation.model_compose_drift_violation import (
    ModelComposeDriftViolation,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Canonical name of the banned-set tuple in service_kernel.py.
BANNED_CONSTANT_NAME: Final[str] = "_DEPRECATED_TOPIC_ENV_VARS"

# Filename patterns recognised as compose / k8s manifests.
_COMPOSE_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^docker-compose.*\.ya?ml$")
_COMPOSE_DIR_COMPONENTS: Final[frozenset[str]] = frozenset({"k8s", "kubernetes"})

# Directories skipped during recursive scan.
_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".tox",
        ".venv",
        "venv",
        ".mypy_cache",
        ".pytest_cache",
    }
)

# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


class ValidatorBannedComposeVars(BaseModel):
    """Kernel-sourced banned env var detector for compose / k8s manifests.

    Stateless — each call to :meth:`check_paths` returns violations without
    mutating instance state. Safe to reuse across calls.

    Args:
        kernel_source_path: Path to ``service_kernel.py`` whose
            ``_DEPRECATED_TOPIC_ENV_VARS`` tuple is the canonical banned set.
            If ``None``, the validator falls back to an empty banned set
            (hard-fail at CLI level — avoids silent pass on misconfig).
        extra_banned: Additional env var names to treat as banned (optional
            supplement for cross-repo cases the kernel tuple doesn't cover).

    Thread Safety:
        Instances are thread-safe because there is no mutable state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kernel_source_path: Path | None = Field(
        default=None,
        description=(
            "Path to service_kernel.py whose _DEPRECATED_TOPIC_ENV_VARS tuple "
            "is the canonical banned set. Required for non-trivial scans."
        ),
    )
    extra_banned: frozenset[str] = Field(
        default_factory=frozenset,
        description="Additional env var names to treat as banned.",
    )

    def banned_env_vars(self) -> frozenset[str]:
        """Return the resolved banned env var set.

        Combines the AST-extracted kernel tuple with any ``extra_banned``
        names supplied at construction. Empty when no sources are configured.
        """
        kernel_set: frozenset[str] = frozenset()
        if self.kernel_source_path is not None:
            kernel_set = extract_banned_env_vars_from_kernel(self.kernel_source_path)
        return kernel_set | self.extra_banned

    def check_paths(self, paths: list[Path]) -> list[ModelComposeDriftViolation]:
        """Scan the given files/directories and return every drift violation."""
        banned = self.banned_env_vars()
        if not banned:
            return []

        manifests: list[tuple[Path, str]] = []
        for base in paths:
            for file_path in _iter_yaml_files(base):
                if not _is_compose_or_k8s_file(file_path):
                    continue
                text = _read_text_safely(file_path)
                if text is not None:
                    manifests.append((file_path, text))
        return find_banned_env_violations(manifests, banned)


def find_banned_env_violations(
    manifests: list[tuple[Path, str]], banned: frozenset[str]
) -> list[ModelComposeDriftViolation]:
    """Return every banned-env-var violation in already-loaded manifest text.

    Pure counterpart of :meth:`ValidatorBannedComposeVars.check_paths`: no
    filesystem access. Entries whose path is not a compose / k8s manifest are
    ignored.

    Args:
        manifests: ``(path, yaml_text)`` pairs; the path is a label and drives
            compose / k8s recognition.
        banned: Env var names to flag.
    """
    violations: list[ModelComposeDriftViolation] = []

    if not banned:
        return violations

    for file_path, text in manifests:
        if not _is_compose_or_k8s_file(file_path):
            continue
        for var_name, value in _extract_env_pairs_from_text(text):
            if var_name not in banned:
                continue
            violations.append(
                ModelComposeDriftViolation(
                    kind=EnumComposeDriftKind.BANNED_VAR,
                    var_name=var_name,
                    compose_path=file_path,
                    contract_path=None,
                    message=(
                        f"{file_path} exposes banned env var "
                        f"{var_name!r} (value: {value!r}). This var "
                        f"is in the kernel's "
                        f"{BANNED_CONSTANT_NAME} tuple; code no "
                        f"longer reads it (OMN-8784). Remove the "
                        f"entry from compose/k8s."
                    ),
                )
            )

    violations.sort(
        key=lambda v: (
            v.kind.value,
            v.var_name,
            str(v.compose_path or v.contract_path),
        )
    )
    return violations


# ---------------------------------------------------------------------------
# AST-based kernel constant extractor
# ---------------------------------------------------------------------------


def extract_banned_env_vars_from_kernel(kernel_path: Path) -> frozenset[str]:
    """Extract ``_DEPRECATED_TOPIC_ENV_VARS`` string literals from a kernel source file.

    Parses the file with :mod:`ast` and walks module-level ``Assign`` /
    ``AnnAssign`` nodes. Only string-literal tuple / list / set members are
    returned — anything non-literal (expressions, imports) is skipped.

    Returns an empty frozenset if the constant is missing, the file is
    unreadable, or the file cannot be parsed — callers hard-fail on empty.

    This is a static read — no code is executed.
    """
    try:
        source = kernel_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return frozenset()

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return frozenset()

    for node in tree.body:
        targets: list[ast.expr] = []
        value: ast.expr | None = None

        if isinstance(node, ast.Assign):
            targets = list(node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value

        if value is None:
            continue

        for target in targets:
            if isinstance(target, ast.Name) and target.id == BANNED_CONSTANT_NAME:
                return _collect_string_literals(value)

    return frozenset()


def _collect_string_literals(node: ast.expr) -> frozenset[str]:
    """Collect every ``ast.Constant`` string inside a tuple/list/set expression."""
    names: set[str] = set()
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                names.add(element.value)
    return frozenset(names)


# ---------------------------------------------------------------------------
# Compose / k8s scanning helpers
# ---------------------------------------------------------------------------


def _iter_yaml_files(base: Path) -> list[Path]:
    """Return every YAML file under ``base`` (file or directory)."""
    if base.is_file():
        return [base] if base.suffix in {".yaml", ".yml"} else []
    if not base.is_dir():
        return []

    results: list[Path] = []
    for child in base.rglob("*"):
        if any(part in _SKIP_DIRS for part in child.parts):
            continue
        if child.is_file() and child.suffix in {".yaml", ".yml"}:
            results.append(child)
    return sorted(results)


def _is_compose_or_k8s_file(path: Path) -> bool:
    if _COMPOSE_NAME_PATTERN.match(path.name):
        return True
    return any(component in _COMPOSE_DIR_COMPONENTS for component in path.parts)


def _read_text_safely(path: Path) -> str | None:
    """Return the file text, or ``None`` on any read failure."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None


def _parse_yaml_documents(text: str) -> list[object]:
    """Return every document in ``text`` as a list.

    k8s manifests commonly use multi-document YAML streams (``---`` separator)
    bundling a Deployment + Service + ConfigMap in one file. Using
    :func:`yaml.safe_load` on such a stream raises ``ComposerError``; we must
    use :func:`yaml.safe_load_all` to iterate each document.

    Returns an empty list on any parse failure.
    """
    try:
        return [doc for doc in yaml.safe_load_all(text) if doc is not None]
    except yaml.YAMLError:
        return []


def _extract_env_pairs_from_text(text: str) -> list[tuple[str, str]]:
    """Return every ``(var_name, value)`` pair from every YAML document in ``text``."""
    pairs: list[tuple[str, str]] = []
    for doc in _parse_yaml_documents(text):
        pairs.extend(_walk_env_pairs(doc))
    return pairs


def _walk_env_pairs(node: object) -> list[tuple[str, str]]:
    """Yield every ``(name, value)`` pair discoverable as container env.

    Since the validator enforces bans on env var **names**, value-less forms
    are surfaced too (name paired with ``""``). That covers:

    - docker-compose ``environment:`` dict (``KEY: value``)
    - docker-compose ``environment:`` list — all three forms:
        * ``- KEY=value`` — explicit value
        * ``- KEY`` — pass-through from host env (no ``=``)
        * ``- {name: KEY, value: VAL}`` — dict with explicit value
        * ``- {name: KEY}`` — dict with no value (also pass-through)
    - k8s ``env:`` list — both forms:
        * ``- {name: KEY, value: VAL}`` — literal value
        * ``- {name: KEY, valueFrom: {...}}`` — sourced from ConfigMap/Secret/etc.

    Missing a form would be a false-negative bypass of the ban.
    """
    pairs: list[tuple[str, str]] = []

    if isinstance(node, dict):
        for key, value in node.items():
            if key == "environment" and isinstance(value, dict):
                for env_key, env_val in value.items():
                    if isinstance(env_val, (str, int, float)):
                        pairs.append((str(env_key), str(env_val)))
                    elif env_val is None:
                        pairs.append((str(env_key), ""))
            elif key == "environment" and isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        if "=" in item:
                            k, _, v = item.partition("=")
                            name = k.strip()
                            if name:
                                pairs.append((name, v.strip()))
                        else:
                            name = item.strip()
                            if name:
                                pairs.append((name, ""))
                    elif isinstance(item, dict) and "name" in item:
                        pairs.append((str(item["name"]), str(item.get("value", ""))))
            elif key == "env" and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "name" in item:
                        pairs.append((str(item["name"]), str(item.get("value", ""))))
            else:
                pairs.extend(_walk_env_pairs(value))
    elif isinstance(node, list):
        for item in node:
            pairs.extend(_walk_env_pairs(item))

    return pairs
