# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Transport-mock lint validator (OMN-13026).

Detects bare ``AsyncMock()`` / ``MagicMock()`` calls that are bound to
EventBus, transport, or Kafka mock surfaces **without** a ``spec=`` or
``spec_set=`` argument.

Background: PR #1181 used ``AsyncMock()`` (no spec) for an ``EventBusKafka``
mock.  Because MagicMock/AsyncMock auto-generate attributes on access, the
test silently passed even though ``EventBusKafka.stop()`` did not exist on the
real class.  The missing ``stop()`` was a runtime-fatal bug; the test never
caught it.

Detection surface
-----------------
A mock call is flagged when **all** of the following hold:

1. The call is ``AsyncMock(...)`` or ``MagicMock(...)`` (any import form).
2. The call has **no** keyword argument named ``spec`` or ``spec_set``.
3. The variable or argument the mock is bound to has a name that matches the
   EventBus / transport surface heuristic.  Matched names include any
   identifier whose lower-cased form contains one of::

       bus, transport, kafka, event_bus, publisher, subscriber

   *or* the mock is passed as the value for a keyword argument whose name
   contains one of those substrings.

Ratchet mode
------------
Pass ``--baseline <yaml-file>`` to load a frozen per-file violation count.
Only violations **above** the baseline count for that file are reported.  This
lets the gate be activated on repos with existing violations without
immediately blocking every PR — new violations are never allowed; existing ones
are tracked in the baseline and must be driven to zero via per-site tickets.

Suppression
-----------
Add ``# transport-mock-ok: <reason>`` on the offending line to suppress a
single finding (e.g. a genuinely untyped stub context where spec cannot be
applied).

Exit codes
----------
``0`` — no violations above the baseline.
``1`` — at least one un-suppressed violation above the baseline.
``2`` — internal error (parse failure, missing baseline file).

Usage::

    # pre-commit (staged files supplied by pre-commit)
    python -m omnibase_core.validators.transport_mock_lint FILE [...]

    # CI (diff against base ref)
    python -m omnibase_core.validators.transport_mock_lint --base origin/dev

    # With ratchet baseline
    python -m omnibase_core.validators.transport_mock_lint \\
        --baseline validation/transport_mock_baseline.yaml FILE [...]
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

try:
    import yaml

    _YAML_AVAILABLE = True
except ModuleNotFoundError:
    _YAML_AVAILABLE = False

__all__ = [
    "MOCK_NAMES",
    "SURFACE_KEYWORDS",
    "SUPPRESSION_TOKEN",
    "Finding",
    "validate_file",
    "validate_paths",
    "main",
]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Names of mock constructors to flag (case-sensitive — match AST Name.id).
MOCK_NAMES: frozenset[str] = frozenset({"AsyncMock", "MagicMock"})

# Lower-case substrings that identify an EventBus / transport surface variable.
# Matched against the lower-cased identifier name of either:
#   - the assignment target (lhs), or
#   - the keyword argument name (for keyword-argument call sites).
SURFACE_KEYWORDS: tuple[str, ...] = (
    "bus",
    "transport",
    "kafka",
    "event_bus",
    "publisher",
    "subscriber",
)

SUPPRESSION_TOKEN = "# transport-mock-ok:"

_EXCLUDED_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "node_modules",
        ".git",
        "archived",
        "archive",
    }
)


# ---------------------------------------------------------------------------
# Finding data class (internal-dataclass-ok: validator-internal finding)
# ---------------------------------------------------------------------------


class Finding:
    """A single bare-mock-on-transport-surface violation."""

    __slots__ = ("col", "line", "mock_name", "path", "reason", "surface_name")

    def __init__(
        self,
        path: Path,
        line: int,
        col: int,
        mock_name: str,
        surface_name: str,
        reason: str,
    ) -> None:
        self.path = path
        self.line = line
        self.col = col
        self.mock_name = mock_name
        self.surface_name = surface_name
        self.reason = reason

    def format(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.col + 1}: "
            f"bare {self.mock_name}() bound to '{self.surface_name}' "
            f"without spec=/spec_set= ({self.reason})"
        )


# ---------------------------------------------------------------------------
# AST analysis helpers
# ---------------------------------------------------------------------------


def _is_bare_mock_call(node: ast.expr) -> str | None:
    """Return the mock name if ``node`` is a bare AsyncMock()/MagicMock() call.

    "Bare" means: no ``spec`` or ``spec_set`` keyword argument.
    Returns ``None`` if the call is not a bare mock.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    # Support bare ``AsyncMock(...)`` and ``mock.AsyncMock(...)``.
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    else:
        return None
    if name not in MOCK_NAMES:
        return None
    # Check for spec= / spec_set= keyword argument.
    for kw in node.keywords:
        if kw.arg in ("spec", "spec_set"):
            return None
    return name


def _matches_surface(identifier: str) -> bool:
    """True when *identifier* (lower-cased) contains a surface keyword."""
    lower = identifier.lower()
    return any(kw in lower for kw in SURFACE_KEYWORDS)


def _source_lines(source: str) -> list[str]:
    return source.splitlines()


def _is_suppressed(line_text: str) -> bool:
    return SUPPRESSION_TOKEN in line_text


def _find_findings(path: Path, source: str) -> list[Finding]:
    """Walk the AST and return all bare-mock-on-transport-surface violations."""
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    lines = _source_lines(source)
    findings: list[Finding] = []

    for node in ast.walk(tree):
        # Case 1: simple assignment  event_bus = AsyncMock()
        if isinstance(node, ast.Assign):
            mock_name = _is_bare_mock_call(node.value)
            if mock_name is None:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and _matches_surface(target.id):
                    lineno = node.lineno - 1
                    line_text = lines[lineno] if lineno < len(lines) else ""
                    if _is_suppressed(line_text):
                        continue
                    findings.append(
                        Finding(
                            path=path,
                            line=node.lineno,
                            col=node.col_offset,
                            mock_name=mock_name,
                            surface_name=target.id,
                            reason="assignment target name matches transport surface",
                        )
                    )

        # Case 2: annotated assignment  event_bus: SomeType = AsyncMock()
        elif isinstance(node, ast.AnnAssign):
            if node.value is None:
                continue
            mock_name = _is_bare_mock_call(node.value)
            if mock_name is None:
                continue
            target = node.target
            if isinstance(target, ast.Name) and _matches_surface(target.id):
                lineno = node.lineno - 1
                line_text = lines[lineno] if lineno < len(lines) else ""
                if _is_suppressed(line_text):
                    continue
                findings.append(
                    Finding(
                        path=path,
                        line=node.lineno,
                        col=node.col_offset,
                        mock_name=mock_name,
                        surface_name=target.id,
                        reason="annotated assignment target name matches transport surface",
                    )
                )

        # Case 3: keyword argument at a call site  SomeClass(event_bus=AsyncMock())
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg is None:
                    continue
                mock_name = _is_bare_mock_call(kw.value)
                if mock_name is None:
                    continue
                if _matches_surface(kw.arg):
                    lineno = kw.value.lineno - 1
                    line_text = lines[lineno] if lineno < len(lines) else ""
                    if _is_suppressed(line_text):
                        continue
                    findings.append(
                        Finding(
                            path=path,
                            line=kw.value.lineno,
                            col=kw.value.col_offset,
                            mock_name=mock_name,
                            surface_name=kw.arg,
                            reason="keyword argument name matches transport surface",
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# File / path validation
# ---------------------------------------------------------------------------


def _is_test_file(path: Path) -> bool:
    name = path.name
    return (
        name.startswith("test_") or name.endswith("_test.py")
    ) and path.suffix == ".py"


def _should_scan(path: Path) -> bool:
    """True when ``path`` is a test Python file that should be scanned."""
    if not _is_test_file(path):
        return False
    parts = set(path.parts)
    return not (parts & _EXCLUDED_PATH_PARTS)


def validate_file(path: Path) -> list[Finding]:
    """Validate a single file and return all findings."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return _find_findings(path, source)


def validate_paths(paths: Sequence[Path]) -> list[Finding]:
    """Validate all supplied paths, scanning only eligible test files."""
    findings: list[Finding] = []
    for path in paths:
        if path.is_dir():
            for child in _iter_python_files(path):
                if _should_scan(child):
                    findings.extend(validate_file(child))
        elif _should_scan(path):
            findings.extend(validate_file(path))
    return findings


def _iter_python_files(root: Path) -> list[Path]:
    return [
        p
        for p in root.rglob("*.py")
        if not any(part in _EXCLUDED_PATH_PARTS for part in p.parts)
    ]


# ---------------------------------------------------------------------------
# Baseline (ratchet) support
# ---------------------------------------------------------------------------


def _load_baseline(baseline_path: Path) -> dict[str, int]:
    """Load a YAML baseline file mapping relative path -> allowed violation count."""
    if not _YAML_AVAILABLE:
        sys.stderr.write(
            "transport-mock-lint: PyYAML not available; cannot load baseline. "
            "Install pyyaml or run without --baseline.\n"
        )
        raise SystemExit(2)
    try:
        raw = yaml.safe_load(baseline_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        sys.stderr.write(
            f"transport-mock-lint: cannot load baseline {baseline_path}: {exc}\n"
        )
        raise SystemExit(2) from exc
    if not isinstance(raw, dict):
        sys.stderr.write(
            f"transport-mock-lint: baseline {baseline_path} must be a YAML mapping.\n"
        )
        raise SystemExit(2)
    return {str(k): int(v) for k, v in raw.items()}


def _apply_baseline(
    findings: list[Finding],
    baseline: dict[str, int],
) -> list[Finding]:
    """Filter out findings that are within the baseline allowance for their file."""
    from collections import Counter

    counts: Counter[str] = Counter()
    remaining: list[Finding] = []
    for finding in findings:
        key = str(finding.path)
        # Normalize to relative path for baseline lookup (try both forms).
        rel_key = _best_baseline_key(finding.path, baseline)
        allowed = baseline.get(rel_key, baseline.get(key, 0))
        if counts[rel_key] < allowed:
            counts[rel_key] += 1
        else:
            remaining.append(finding)
    return remaining


def _rel_path(path: Path, cwd: Path) -> str:
    """Return a portable relative path string for *path* against *cwd*.

    Falls back to the absolute path string if *path* is not relative to *cwd*.
    Ensures --write-baseline outputs portable keys that work across machines.
    """
    try:
        return str(path.relative_to(cwd))
    except ValueError:
        return str(path)


def _best_baseline_key(path: Path, baseline: dict[str, int]) -> str:
    """Return the baseline key that best matches *path* (exact, then suffix match)."""
    path_str = str(path)
    if path_str in baseline:
        return path_str
    # Try matching by the portion of the path after "tests/"
    for key in baseline:
        if path_str.endswith((key, key.replace("/", "\\"))):
            return key
    return path_str


# ---------------------------------------------------------------------------
# Git helpers (CI mode)
# ---------------------------------------------------------------------------


def _git_changed_files(base: str) -> list[Path]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(2)
    return [Path(p) for p in proc.stdout.splitlines() if p.strip()]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="transport-mock-lint",
        description=(
            "Detect bare AsyncMock()/MagicMock() without spec=/spec_set= "
            "on EventBus/transport/Kafka mock surfaces (OMN-13026)."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Explicit file or directory paths to scan (pre-commit passes staged files).",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Git base ref to diff HEAD against (CI mode).",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="YAML ratchet baseline file mapping relative-path -> allowed-count.",
    )
    parser.add_argument(
        "--write-baseline",
        default=None,
        metavar="OUT",
        help=(
            "Instead of checking, scan and write current violation counts to OUT "
            "as a YAML ratchet baseline."
        ),
    )
    args = parser.parse_args(argv)

    if args.base is not None:
        paths = _git_changed_files(args.base)
    else:
        paths = [Path(p) for p in args.files]

    if not paths:
        # No files supplied — scan nothing (pre-commit passes only staged files).
        return 0

    all_findings = validate_paths(paths)

    if args.write_baseline is not None:
        if not _YAML_AVAILABLE:
            sys.stderr.write(
                "transport-mock-lint: PyYAML not available; cannot write baseline.\n"
            )
            return 2
        from collections import Counter

        cwd = Path.cwd()
        counts: Counter[str] = Counter(_rel_path(f.path, cwd) for f in all_findings)
        out_path = Path(args.write_baseline)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            yaml.dump(dict(counts), fh, default_flow_style=False, sort_keys=True)
        sys.stdout.write(
            f"transport-mock-lint: wrote baseline with {len(counts)} files "
            f"({sum(counts.values())} total violations) to {out_path}\n"
        )
        return 0

    baseline: dict[str, int] = {}
    if args.baseline is not None:
        baseline = _load_baseline(Path(args.baseline))

    active_findings = (
        _apply_baseline(all_findings, baseline) if baseline else all_findings
    )

    if not active_findings:
        return 0

    sys.stderr.write(
        "transport-mock-lint: FAIL — bare mock(s) on transport surface:\n\n"
    )
    for finding in active_findings:
        sys.stderr.write(f"  {finding.format()}\n")
    sys.stderr.write(
        "\nFix: add spec=<ProtocolClass> or spec_set=<ProtocolClass> to the mock call.\n"
        "     Example: AsyncMock(spec=ProtocolEventBus)\n"
        "     This ensures the mock only exposes methods that exist on the real class.\n"
        f"Reference incident: PR #1181 — bare AsyncMock hid missing EventBusKafka.stop().\n"
        f"Suppression: add '{SUPPRESSION_TOKEN} <reason>' on the offending line.\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
