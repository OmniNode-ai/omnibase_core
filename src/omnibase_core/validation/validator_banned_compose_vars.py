# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ValidatorBannedComposeVars — bidirectional compose↔contract topic drift.

Builds the canonical set of ONEX topics declared by ``event_bus.subscribe_topics``
/ ``publish_topics`` across every ``contract.yaml`` in the scanned tree, then
compares against Docker-compose and Kubernetes manifest environment blocks.

Two drift kinds are reported:

- **BANNED_VAR**: compose/k8s references an ONEX topic string (via any env var
  value) that no contract declares. Stale compose — the OMN-8840 pattern where
  ``ONEX_INPUT_TOPIC`` persisted after OMN-8784 removed the topic from code.
- **MISSING_VAR**: a contract declares a topic but no compose / k8s manifest
  exposes it as any env var value. Orphaned contract.

The validator deliberately ignores non-ONEX env var values (plain strings like
``requests``, ``responses``) — the universe of drift it gates is ONEX topic
strings matching ``onex.{kind}.{producer}.{event-name}.v{n}``.

Related ticket: OMN-9062 (trigger: OMN-8840, parent: OMN-9048).

Usage::

    # Programmatic
    from pathlib import Path
    from omnibase_core.validation import ValidatorBannedComposeVars

    validator = ValidatorBannedComposeVars()
    violations = validator.check_paths([Path("omni_home")])

    # CLI
    python -m omnibase_core.validation.validator_banned_compose_vars omni_home/

Exit codes:
    0 — no drift
    2 — drift detected
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Final

import yaml
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_compose_drift_kind import EnumComposeDriftKind
from omnibase_core.models.validation.model_compose_drift_violation import (
    ModelComposeDriftViolation,
)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Canonical ONEX topic form: onex.{kind}.{producer}.{event-name}.v{n}
# Kept in lock-step with validator_topic_suffix.TOPIC_SUFFIX_PATTERN.
_ONEX_TOPIC_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^onex\.(cmd|evt|dlq|intent|snapshot)\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.v\d+$"
)

# Filename patterns recognised as compose / k8s manifests.
_COMPOSE_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(r"^docker-compose.*\.ya?ml$")
_COMPOSE_DIR_COMPONENTS: Final[frozenset[str]] = frozenset({"k8s", "kubernetes"})

# Contract filenames (scanned for topic declarations).
_CONTRACT_FILENAMES: Final[frozenset[str]] = frozenset(
    {"contract.yaml", "contract.yml", "handler_contract.yaml"}
)

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
    """Bidirectional compose↔contract topic drift detector.

    Stateless — each call to :meth:`check_paths` returns violations without
    mutating instance state. Safe to reuse across calls.

    Thread Safety:
        Instances are thread-safe because there is no mutable state.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    def check_paths(self, paths: list[Path]) -> list[ModelComposeDriftViolation]:
        """Scan the given files/directories and return every drift violation."""
        # Maps: topic -> source path / (var_name, source) for compose.
        contract_topics: dict[str, Path] = {}
        compose_topics: dict[str, tuple[str, Path]] = {}

        for base in paths:
            for file_path in _iter_yaml_files(base):
                if _is_contract_file(file_path):
                    for topic in _extract_contract_topics(file_path):
                        contract_topics.setdefault(topic, file_path)
                elif _is_compose_or_k8s_file(file_path):
                    for var_name, topic in _extract_compose_topic_refs(file_path):
                        compose_topics.setdefault(topic, (var_name, file_path))

        violations: list[ModelComposeDriftViolation] = []

        # BANNED_VAR: compose references an ONEX topic no contract declares
        for topic, (var_name, compose_path) in compose_topics.items():
            if topic in contract_topics:
                continue
            violations.append(
                ModelComposeDriftViolation(
                    kind=EnumComposeDriftKind.BANNED_VAR,
                    var_name=var_name,
                    compose_path=compose_path,
                    contract_path=None,
                    message=(
                        f"{compose_path} exposes env var {var_name!r} = "
                        f"{topic!r} but no contract.yaml declares that topic "
                        f"in event_bus.subscribe_topics / publish_topics. "
                        f"Either declare the topic in a contract or remove "
                        f"the stale env var from compose/k8s."
                    ),
                )
            )

        # MISSING_VAR: contract declares a topic no compose / k8s exposes
        for topic, contract_path in contract_topics.items():
            if topic in compose_topics:
                continue
            violations.append(
                ModelComposeDriftViolation(
                    kind=EnumComposeDriftKind.MISSING_VAR,
                    var_name=_topic_to_var_hint(topic),
                    compose_path=None,
                    contract_path=contract_path,
                    message=(
                        f"{contract_path} declares topic {topic!r} but no "
                        f"compose / k8s manifest exposes it via any env var. "
                        f"Either wire the topic into compose/k8s or remove "
                        f"the contract declaration."
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
# Helpers (module-private)
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


def _is_contract_file(path: Path) -> bool:
    return path.name in _CONTRACT_FILENAMES


def _is_compose_or_k8s_file(path: Path) -> bool:
    if _COMPOSE_NAME_PATTERN.match(path.name):
        return True
    return any(component in _COMPOSE_DIR_COMPONENTS for component in path.parts)


def _load_yaml_safely(path: Path) -> object | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return None
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError:
        return None


def _extract_contract_topics(path: Path) -> list[str]:
    """Extract every ONEX topic declared by this contract's event_bus block."""
    doc = _load_yaml_safely(path)
    if not isinstance(doc, dict):
        return []
    event_bus = doc.get("event_bus")
    if not isinstance(event_bus, dict):
        return []

    topics: list[str] = []
    for key in ("subscribe_topics", "publish_topics"):
        raw = event_bus.get(key)
        if isinstance(raw, list):
            topics.extend(str(item) for item in raw if isinstance(item, str))

    return [topic for topic in topics if _ONEX_TOPIC_PATTERN.match(topic)]


def _extract_compose_topic_refs(path: Path) -> list[tuple[str, str]]:
    """Extract every ``(var_name, topic)`` pair whose value is an ONEX topic.

    Handles three forms:

    - docker-compose ``environment:`` dict (``KEY: value``)
    - docker-compose ``environment:`` list (``- KEY=value`` or ``- KEY: value``)
    - k8s ``env:`` list of ``{name: KEY, value: VAL}``
    """
    doc = _load_yaml_safely(path)
    if doc is None:
        return []

    return [
        (var_name, value)
        for var_name, value in _walk_env_pairs(doc)
        if _ONEX_TOPIC_PATTERN.match(value)
    ]


def _walk_env_pairs(node: object) -> list[tuple[str, str]]:
    """Yield every ``(name, value)`` pair discoverable as container env."""
    pairs: list[tuple[str, str]] = []

    if isinstance(node, dict):
        for key, value in node.items():
            if key == "environment" and isinstance(value, dict):
                for env_key, env_val in value.items():
                    if isinstance(env_val, (str, int, float)):
                        pairs.append((str(env_key), str(env_val)))
            elif key == "environment" and isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and "=" in item:
                        k, _, v = item.partition("=")
                        pairs.append((k.strip(), v.strip()))
                    elif isinstance(item, dict) and "name" in item and "value" in item:
                        pairs.append((str(item["name"]), str(item["value"])))
            elif key == "env" and isinstance(value, list):
                for item in value:
                    if isinstance(item, dict) and "name" in item and "value" in item:
                        pairs.append((str(item["name"]), str(item["value"])))
            else:
                pairs.extend(_walk_env_pairs(value))
    elif isinstance(node, list):
        for item in node:
            pairs.extend(_walk_env_pairs(item))

    return pairs


def _topic_to_var_hint(topic: str) -> str:
    """Produce a human-readable identifier for MISSING_VAR reports.

    Contracts declare topics, not env var names; this surfaces the topic
    itself as the "var_name" so consumers of the report can locate it.
    """
    return f"<missing-topic:{topic}>"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint.

    Exit codes:
        0 — no drift
        2 — drift detected
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="check-banned-compose-vars",
        description=(
            "Detect bidirectional compose↔contract topic drift. "
            "Exits 2 if any BANNED_VAR or MISSING_VAR violation is found."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[Path()],
        help="Files or directories to scan (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress the summary footer",
    )
    parsed = parser.parse_args(argv)

    validator = ValidatorBannedComposeVars()
    violations = validator.check_paths(parsed.paths)

    for v in violations:
        location = v.compose_path if v.compose_path is not None else v.contract_path
        print(f"{location}: [{v.kind.value}] {v.var_name}: {v.message}")

    if not parsed.quiet:
        if violations:
            banned = sum(
                1 for v in violations if v.kind is EnumComposeDriftKind.BANNED_VAR
            )
            missing = sum(
                1 for v in violations if v.kind is EnumComposeDriftKind.MISSING_VAR
            )
            print(
                f"\n{len(violations)} compose/contract drift violation(s): "
                f"{banned} BANNED_VAR, {missing} MISSING_VAR.",
                file=sys.stderr,
            )
        else:
            print("No compose/contract drift found.", file=sys.stderr)

    return 2 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
