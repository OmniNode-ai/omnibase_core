# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Ratchet gate against non-canonical lifecycle-word classes (OMN-14350).

The canonical architecture (``docs/architecture/ONEX_CANONICAL_ARCHITECTURE.md``)
is three primitives — CONTRACT, NODE, HANDLER — and nothing else: "no bespoke
classes/engines/adapters/routers/daemons/registries/managers/runners survive
anywhere." This validator flags class definitions whose CamelCase name carries a
non-canonical *type-word* (``Service``, ``Engine``, ``Adapter``, ``Router``,
``Daemon``, ``Manager``, ``Runner``, ``Registry``, ``Controller``, ``Server``,
``Client``) and ratchets the count DOWN toward zero.

It is an allowlist ratchet, not a hard prohibition. A frozen baseline of the
repo's *current* residual FQNs lives in
``noncanonical_class_allowlist.yaml``. The gate passes iff no NEW hard-fail class
appears outside that baseline. ``--check-stale`` fails if an allowlisted FQN no
longer exists in the tree — the count may only shrink, never coast.

False-positive exclusions (canonical constructs that legitimately carry a
type-word) are baked in — see ``_is_excluded``. Underscore-private classes are
routed to a report-only soft list, never the hard-fail set.

Usage::

    # pre-commit / staged files (whole-src arg forces a full ratchet scan)
    python -m omnibase_core.validators.no_noncanonical_lifecycle_classes src/omnibase_core

    # CI — full scan plus stale-entry enforcement
    python -m omnibase_core.validators.no_noncanonical_lifecycle_classes \
        --check-stale src/omnibase_core

DoD reference: OMN-14350 (non-canonical-class ratchet, omnibase_core canary).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import yaml

from omnibase_core.models.validation.model_noncanonical_class_finding import (
    ModelNoncanonicalClassFinding,
)

DEFAULT_SCAN_ROOT = Path("src/omnibase_core")
DEFAULT_ALLOWLIST_PATH = Path(__file__).with_name("noncanonical_class_allowlist.yaml")

# ---------------------------------------------------------------------------
# Type-word taxonomy (the non-canonical lifecycle vocabulary being ratcheted).
# ---------------------------------------------------------------------------
TYPE_WORDS: frozenset[str] = frozenset(
    {
        "Service",
        "Engine",
        "Adapter",
        "Router",
        "Daemon",
        "Manager",
        "Runner",
        "Registry",
        "Controller",
        "Server",
        "Client",
    }
)

# ---------------------------------------------------------------------------
# False-positive exclusions — canonical constructs that carry a type-word.
# ---------------------------------------------------------------------------
# A leading CamelCase word that marks a canonical construct (DTO, protocol,
# archetype, test double). Compared as a leading whole-word prefix so that e.g.
# ``Modeler`` does not match ``Model``.
FIRST_WORD_ALLOW: frozenset[str] = frozenset(
    {
        "Protocol",
        "Model",
        "Enum",
        "TypedDict",
        "Mixin",
        "Node",
        "Handler",
        "Mock",
        "Fake",
        "Stub",
        "Test",
        "Abstract",
        "Base",
    }
)

# A trailing CamelCase word that marks a passive data-transfer object, not a
# lifecycle owner. ``Protocol`` is handled separately (endswith).
DTO_SUFFIXES: frozenset[str] = frozenset(
    {
        "Error",
        "Result",
        "Snapshot",
        "Info",
        "Stats",
        "Spec",
        "Payload",
        "State",
        "Config",
        "Settings",
    }
)

# ``Registry`` + one of these archetype suffixes is the canonical per-node DI
# registry naming, not a bespoke registry.
REGISTRY_ARCHETYPE_SUFFIXES: frozenset[str] = frozenset(
    {
        "Effect",
        "Compute",
        "Reducer",
        "Orchestrator",
        "Handler",
        "Node",
    }
)

# Per-node DI registry file locations (canonical per the CLAUDE.md naming table).
_REGISTRY_PATH_RE = re.compile(r"(/registry/registry_[^/]*|/registry_infra_[^/]*)")

# CamelCase / acronym-aware word segmentation.
_SEGMENT_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z0-9]+|[A-Z]+")

_SEVERITY_HARDFAIL = "hardfail"
_SEVERITY_SOFT = "soft"


# ---------------------------------------------------------------------------
# Segmentation / classification helpers
# ---------------------------------------------------------------------------
def _camel_segments(name: str) -> list[str]:
    """Split a CamelCase identifier into its capitalized/acronym word segments."""
    return _SEGMENT_RE.findall(name)


def _starts_with_word(name: str, word: str) -> bool:
    """Return True iff *name* begins with *word* as a whole leading CamelCase word."""
    if not name.startswith(word):
        return False
    rest = name[len(word) :]
    return rest == "" or not rest[0].islower()


def _matched_type_word(name: str) -> str | None:
    """Return the first CamelCase segment that is a non-canonical type-word."""
    for segment in _camel_segments(name):
        if segment in TYPE_WORDS:
            return segment
    return None


def _is_excluded(module: str, class_name: str, posix_path: str) -> bool:
    """Return True for canonical constructs that legitimately carry a type-word."""
    segments = _camel_segments(class_name)
    first = segments[0] if segments else ""

    # 1. Canonical leading word (DTO / protocol / archetype / test double).
    if first in FIRST_WORD_ALLOW or any(
        _starts_with_word(class_name, word) for word in FIRST_WORD_ALLOW
    ):
        return True

    # 2. Passive DTO / protocol suffix.
    if class_name.endswith("Protocol"):
        return True
    if any(class_name.endswith(suffix) for suffix in DTO_SUFFIXES):
        return True

    # 3. Per-node DI registry: name prefix OR canonical file location.
    if class_name.startswith("RegistryInfra"):
        return True
    if _REGISTRY_PATH_RE.search(posix_path):
        return True

    # 4. Registry + archetype suffix (canonical per-node registry naming).
    if class_name.startswith("Registry") and any(
        class_name.endswith(suffix) for suffix in REGISTRY_ARCHETYPE_SUFFIXES
    ):
        return True

    return False


def _classify(module: str, class_name: str, posix_path: str) -> tuple[str, str] | None:
    """Classify a class name.

    Returns ``(severity, matched_word)`` or ``None`` when the class is not a
    non-canonical candidate at all.
    """
    matched = _matched_type_word(class_name)
    if matched is None:
        return None
    # Exclusions win over everything: canonical constructs are not reported.
    if _is_excluded(module, class_name, posix_path):
        return None
    # Underscore-private classes are report-only, never gate-blocking.
    if class_name.startswith("_"):
        return _SEVERITY_SOFT, matched
    return _SEVERITY_HARDFAIL, matched


# ---------------------------------------------------------------------------
# Module-path resolution
# ---------------------------------------------------------------------------
def _module_name(path: Path) -> str:
    """Compute the dotted module path (``omnibase_core.foo.bar``) for a file."""
    parts = path.parts
    src_indices = [i for i, part in enumerate(parts) if part == "src"]
    mod_parts = list(parts[src_indices[-1] + 1 :]) if src_indices else list(parts)
    if mod_parts and mod_parts[-1].endswith(".py"):
        mod_parts[-1] = mod_parts[-1][:-3]
    if mod_parts and mod_parts[-1] == "__init__":
        mod_parts = mod_parts[:-1]
    return ".".join(mod_parts)


# ---------------------------------------------------------------------------
# File / path scanning
# ---------------------------------------------------------------------------
def validate_file(path: Path) -> list[ModelNoncanonicalClassFinding]:
    """Return all non-canonical class findings (hard-fail + soft) in *path*."""
    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    module = _module_name(path)
    posix_path = path.as_posix()
    findings: list[ModelNoncanonicalClassFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        classified = _classify(module, node.name, posix_path)
        if classified is None:
            continue
        severity, matched_word = classified
        findings.append(
            ModelNoncanonicalClassFinding(
                path=path,
                line=node.lineno,
                column=node.col_offset,
                class_name=node.name,
                module=module,
                matched_word=matched_word,
                severity=severity,
            )
        )
    return findings


def validate_paths(paths: Sequence[Path]) -> list[ModelNoncanonicalClassFinding]:
    """Validate every unique Python file under the supplied paths."""
    findings: list[ModelNoncanonicalClassFinding] = []
    for path in _iter_python_files(paths):
        findings.extend(validate_file(path))
    return findings


def _iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    scan_paths = tuple(paths) or (DEFAULT_SCAN_ROOT,)
    seen: set[Path] = set()
    for path in scan_paths:
        if path.is_file() and path.suffix == ".py":
            candidates: Iterator[Path] = iter((path,))
        elif path.is_dir():
            candidates = (
                candidate
                for candidate in sorted(path.rglob("*.py"))
                if "__pycache__" not in candidate.parts
            )
        else:
            continue
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield candidate


# ---------------------------------------------------------------------------
# Allowlist (frozen ratchet baseline)
# ---------------------------------------------------------------------------
def load_allowlist(path: Path) -> set[str]:
    """Load the frozen ``module:ClassName`` FQN allowlist.

    A missing file yields an empty allowlist (fail-closed: any residual is NEW).
    """
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError, OSError):
        return set()
    if not isinstance(data, dict):
        return set()
    entries = data.get("allowlist") or []
    if not isinstance(entries, list):
        return set()
    return {str(entry) for entry in entries if isinstance(entry, str)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ratchet gate against non-canonical lifecycle-word classes "
            "(Service/Engine/Adapter/Router/Daemon/Manager/Runner/Registry/"
            "Controller/Server/Client). New hard-fail classes outside the frozen "
            "allowlist block; the count may only shrink (OMN-14350)."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_SCAN_ROOT],
        help="Python file or directory paths to scan (default: src/omnibase_core).",
    )
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST_PATH,
        help="Path to the frozen FQN allowlist YAML.",
    )
    parser.add_argument(
        "--check-stale",
        action="store_true",
        default=False,
        help=(
            "Also fail if an allowlisted FQN no longer exists in the scanned "
            "tree (forces the count-only-down ratchet discipline)."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    allowlist = load_allowlist(args.allowlist)
    findings = validate_paths(args.paths)

    hardfail = [f for f in findings if f.severity == _SEVERITY_HARDFAIL]
    soft = [f for f in findings if f.severity == _SEVERITY_SOFT]

    present_fqns = {f.fqn for f in hardfail}
    new_residual = [f for f in hardfail if f.fqn not in allowlist]
    stale_entries = sorted(allowlist - present_fqns) if args.check_stale else []

    exit_code = 0

    if new_residual:
        exit_code = 1
        sys.stderr.write(
            "no-noncanonical-lifecycle-classes: NEW non-canonical class(es) "
            "outside the frozen allowlist:\n"
        )
        for finding in new_residual:
            sys.stderr.write(f"  {finding.format()}\n")
        sys.stderr.write(
            "\n  Rename the class to a canonical CONTRACT/NODE/HANDLER shape, or —\n"
            "  only if it is a pre-existing residual being tracked for burn-down —\n"
            "  add its FQN to noncanonical_class_allowlist.yaml. The allowlist is a\n"
            "  ratchet: it may only shrink. See OMN-14350.\n\n"
        )

    if stale_entries:
        exit_code = 1
        sys.stderr.write(
            "no-noncanonical-lifecycle-classes: STALE allowlist entr(y/ies) — the "
            "class no longer exists; remove the line so the count ratchets down:\n"
        )
        for fqn in stale_entries:
            sys.stderr.write(f"  {fqn}\n")
        sys.stderr.write("\n")

    if soft:
        # Report-only: underscore-private candidates never affect the exit code.
        sys.stderr.write(
            "no-noncanonical-lifecycle-classes: soft (report-only) private "
            "candidates — not gate-blocking:\n"
        )
        for finding in soft:
            sys.stderr.write(f"  {finding.format()}\n")
        sys.stderr.write("\n")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: validator CLI process exit
