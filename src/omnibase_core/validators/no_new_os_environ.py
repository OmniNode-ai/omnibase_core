# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Canonical no-new-os-environ validator (OMN-13566).

Blocks ALL ``os.environ[KEY]``, ``os.environ.get(KEY)``, and ``os.getenv(KEY)``
reads outside the explicit ``KEEP_ALLOWLIST`` of structurally required bootstrap
and CI variables.  This converts the platform from "block new vs frozen 685
baseline" to "zero env reads outside the named bootstrap set."

Generalises ``omnibase_infra/scripts/check-env-reads.sh`` (OMN-11069/11186) and
the ``scripts/validation/validate_no_new_env_vars.py`` regex approach into a
single canonical AST-based implementation deployed as a pre-commit hook and CI
job from ``omnibase_core``.

Allowlist policy
----------------
- ``KEEP_ALLOWLIST`` is the ONLY permitted escape.
- Adding a new var requires a PR reviewed by CODEOWNERS.
- Inline suppression (``# env-read-ok: <reason>``) is allowed for one-off
  structural bootstrap lines that are not candidates for the global allowlist.
- Test files (``tests/``) and tooling directories (``scripts/``, ``examples/``)
  are skipped because they legitimately reference env var names as test data or
  in operational bootstrap tooling.

Usage
-----
Pre-commit (staged files)::

    python -m omnibase_core.validators.no_new_os_environ file1.py file2.py ...

CI — full repo scan::

    python -m omnibase_core.validators.no_new_os_environ --all --src src/

Suppression
-----------
Add ``# env-read-ok: <reason>`` on the offending line.

DoD reference: OMN-13566 (Wave-4 env-read enforcement ratchet).
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Keep allowlist — ONLY approved bootstrap / path-resolution / CI env vars.
# Extend via PR reviewed by CODEOWNERS — never auto-expand.
# ---------------------------------------------------------------------------
KEEP_ALLOWLIST: frozenset[str] = frozenset(
    {
        # Cross-machine identity / path resolution
        "OMNI_HOME",
        "OMNI_WORKTREES",
        "OMNIMARKET_ROOT",
        "ONEX_SRC_DIR",
        "PATH",
        "HOME",
        "USER",
        "HOSTNAME",
        "TMPDIR",
        "TEMP",
        "TMP",
        "XDG_RUNTIME_DIR",
        # CI environment detection
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "CI_RUNNER_TYPE",
        "JENKINS_URL",
        "GITHUB_TOKEN",
        "GITHUB_SHA",
        "GITHUB_REF",
        "GITHUB_REF_NAME",
        "GITHUB_HEAD_REF",
        "GITHUB_BASE_REF",
        "GITHUB_REPOSITORY",
        "GITHUB_WORKSPACE",
        "GITHUB_OUTPUT",
        "GITHUB_STEP_SUMMARY",
        "GITHUB_ENV",
        "RUNNER_TEMP",
        "RUNNER_TOOL_CACHE",
        "RUNNER_OS",
        "RUNNER_ARCH",
        # ONEX runtime state roots
        "ONEX_EVIDENCE_ROOT",
        "ONEX_WORKTREES_ROOT",
        "ONEX_STATE_ROOT",
        "ONEX_STATE_DIR",
        "ONEX_CORRELATION_ID",
        "ONEX_HOOKS_MASK",
        "ONEX_RUNTIME_CONTRACTS_DIR",
        "ONEX_CONTEXT_SIZE_WARN_ON_CREATE",
        "ONEX_DEBUG_THREAD_SAFETY",
        "ONEX_VALIDATION_MODE",
        # ONEX event bus config (grandfathered at OMN-11186 activation)
        "ONEX_EVENT_BUS_BOOTSTRAP_SERVERS",
        "ONEX_EVENT_BUS_TOPICS",
        "ONEX_EVENT_BUS_ENABLE_AUTO_COMMIT",
        "ONEX_EVENT_BUS_PARTITIONS",
        "ONEX_EVENT_BUS_PRIORITY",
        "ONEX_EVENT_BUS_REPLICATION_FACTOR",
        "ONEX_EVENT_BUS_SASL_MECHANISM",
        "ONEX_EVENT_BUS_SASL_PASSWORD",
        "ONEX_EVENT_BUS_SASL_USERNAME",
        "ONEX_EVENT_BUS_SECURITY_PROTOCOL",
        "ONEX_EVENT_BUS_TIMEOUT_SECONDS",
        # Kafka / event bus bootstrap (pre-existing; migrate to contract when feasible)
        "KAFKA_BOOTSTRAP_SERVERS",
        "EVENT_BUS_BOOTSTRAP_SERVERS",
        "EVENT_BUS_TOPICS",
        # Postgres (doctor + diagnostic tooling)
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_PASSWORD",
        "POSTGRES_USER",
        "POSTGRES_DB",
        # Valkey / Redis diagnostic
        "VALKEY_HOST",
        "VALKEY_PORT",
        "REDIS_URL",
        # Infisical bootstrap
        "INFISICAL_ADDR",
        "INFISICAL_TOKEN",
        "INFISICAL_CLIENT_ID",
        "INFISICAL_CLIENT_SECRET",
        # OMNIBASE_ALLOWED_NAMESPACES
        "OMNIBASE_ALLOWED_NAMESPACES",
        # OMNIBASE_CORE_PATH (used during pre-commit before install)
        "OMNIBASE_CORE_PATH",
        # Linear (doctor checks only)
        "LINEAR_API_KEY",
        # LLM endpoints (inference tooling)
        "LLM_LOCAL_MODEL",
        "LLM_LOCAL_URL",
        # ONEX agent / plugin paths
        "OMNICLAUDE_AGENTS_PATH",
        # Contract enforcement overrides
        "CONTRACT_REQUIRED_AFTER",
        "PLAN_CONTRACT_REQUIRED_AFTER",
        # DB circuit breaker tuning
        "DB_CIRCUIT_BREAKER_FAILURE_THRESHOLD",
        "DB_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS",
        "DB_CIRCUIT_BREAKER_RECOVERY_TIMEOUT",
        # Generic config used in existing tests / validators
        "DEBUG",
        "DEBUG_MODE",
        "ENVIRONMENT",
        "NODE_ENV",
        "LOG_LEVEL",
        "NODE_ID",
        "NODE_VERSION",
        "SERVICE_PORT",
        "MAX_WORKFLOWS",
        "WORKFLOW_TIMEOUT",
        "METRICS_ENABLED",
        "METRICS_PORT",
        "HEALTH_CHECK_ENABLED",
        "HEALTH_CHECK_INTERVAL",
        "HEALTH_CHECK_TIMEOUT",
        # Scripts / validation tooling
        "DETERMINISTIC_SKILL_ROOT",
        "ZONE_DIFF_FILTER_FAKE_DIFF",
        # PYTHONPATH (tooling launchers)
        "PYTHONPATH",
        # Artifact store (CLI seam; OMN-13537)
        "ONEX_ARTIFACT_STORE_ROOT",
        # Config discovery / overlay resolver (bootstrap seam)
        "ONEX_OVERLAY_DIR",
        "ONEX_RUNTIME_PROFILE",
        "ONEX_CONFIG_DIR",
        "ONEX_CONTRACTS_ROOT",
        # OMNI_HOME-relative path roots
        "OMNI_PROJECTS_ROOT",
        "OMNI_SKILLS_ROOT",
        # OpenTelemetry / tracing
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_SERVICE_NAME",
        "OTEL_TRACES_EXPORTER",
        "OTEL_RESOURCE_ATTRIBUTES",
        # Phoenix / observability
        "PHOENIX_HOST",
        "PHOENIX_PORT",
        # Google / ADC bootstrap
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_API_KEY",
        # GitHub secondary PAT (hooks only — api_key_ref is the canonical route)
        "GH_PAT",
        "GH_TOKEN",
        # Docker / container plumbing
        "DOCKER_HOST",
        "DOCKER_BUILDKIT",
        "COMPOSE_FILE",
        "COMPOSE_PROJECT_NAME",
        # Python runtime / packaging tooling
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "PIP_INDEX_URL",
        "PIP_NO_CACHE_DIR",
        # SSL / TLS
        "SSL_CERT_FILE",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        # Pytest / test tooling
        "PYTEST_CURRENT_TEST",
        "PYTEST_XDIST_WORKER",
        "PYTEST_XDIST_WORKER_COUNT",
        # Kubernetes platform detection (structural bootstrap seam)
        "KUBERNETES_SERVICE_HOST",
        "KUBERNETES_SERVICE_PORT",
        "KUBERNETES_NAMESPACE",
        # Service host (infrastructure bootstrap)
        "SERVICE_HOST",
        # misc platform vars legitimately checked in cross-platform code
        "USERPROFILE",  # Windows HOME equivalent
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMFILES",
        "SYSTEMROOT",
        "COMSPEC",
        "TERM",
        "COLORTERM",
        "FORCE_COLOR",
        "NO_COLOR",
        "CLICOLOR",
        # ONEX test isolation
        "ONEX_TEST_ISOLATION",
        "ONEX_TEST_BUS_BACKEND",
        "ONEX_SKIP_RUNTIME_CHECK",
        # OMNI_HOME companion vars
        "OMNI_RUNNER_SELECTOR_V1",
    }
)

# Inline suppression annotation
_SUPPRESSION_TOKEN = "# env-read-ok"

# Directories to skip unconditionally (pre-commit passes individual files, but
# validate_file is also called directly from validate_paths which walks dirs).
_SKIP_DIR_SEGMENTS: frozenset[str] = frozenset({"tests", "scripts", "examples"})


# ---------------------------------------------------------------------------
# Finding dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EnvReadFinding:
    """One env-read violation found by the validator."""

    path: Path
    line: int
    col: int
    var_name: str
    raw_line: str

    def format(self) -> str:
        return (
            f"{self.path}:{self.line}:{self.col}: "
            f"os.environ/os.getenv read of {self.var_name!r} "
            f"outside KEEP_ALLOWLIST"
        )


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------


class _EnvReadVisitor(ast.NodeVisitor):
    """Walk an AST looking for os.environ / os.getenv reads."""

    def __init__(self, source_lines: list[str]) -> None:
        self._lines = source_lines
        self.findings: list[tuple[int, int, str]] = []  # (line, col, var_name)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect os.environ[KEY]."""
        if _is_os_environ_attr(node.value):
            var_name = _extract_constant_string(node.slice)
            if var_name is not None and self._should_flag(node.lineno, var_name):
                self.findings.append((node.lineno, node.col_offset, var_name))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect os.environ.get(KEY) and os.getenv(KEY)."""
        if _is_os_environ_get(node.func) or _is_os_getenv(node.func):
            var_name = _first_arg_string(node)
            if var_name is not None and self._should_flag(node.lineno, var_name):
                self.findings.append((node.lineno, node.col_offset, var_name))
        self.generic_visit(node)

    def _should_flag(self, lineno: int, var_name: str) -> bool:
        if var_name in KEEP_ALLOWLIST:
            return False
        raw = self._lines[lineno - 1] if lineno <= len(self._lines) else ""
        return _SUPPRESSION_TOKEN not in raw


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _is_os_environ_attr(node: ast.expr) -> bool:
    """Return True for the ``os.environ`` attribute expression."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "environ"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _is_os_environ_get(node: ast.expr) -> bool:
    """Return True for ``os.environ.get`` attribute chain."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "get"
        and _is_os_environ_attr(node.value)
    )


def _is_os_getenv(node: ast.expr) -> bool:
    """Return True for ``os.getenv`` attribute expression."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "getenv"
        and isinstance(node.value, ast.Name)
        and node.value.id == "os"
    )


def _extract_constant_string(node: ast.expr) -> str | None:
    """Extract a string constant from a subscript slice."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _first_arg_string(node: ast.Call) -> str | None:
    """Extract the first positional argument as a string constant, if any."""
    if node.args:
        return _extract_constant_string(node.args[0])
    return None


# ---------------------------------------------------------------------------
# Path skip logic
# ---------------------------------------------------------------------------


def _should_skip_path(path: Path) -> bool:
    """Return True for non-Python files or files inside skipped directories."""
    if path.suffix != ".py":
        return True
    return any(seg in _SKIP_DIR_SEGMENTS for seg in path.parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_file(path: Path) -> list[EnvReadFinding]:
    """Return all env-read violations in *path*.

    Returns an empty list when the file should be skipped (test/scripts dir,
    non-Python, unreadable) or is clean.
    """
    if _should_skip_path(path):
        return []

    try:
        source = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    lines = source.splitlines()
    visitor = _EnvReadVisitor(lines)
    visitor.visit(tree)

    return [
        EnvReadFinding(
            path=path,
            line=lineno,
            col=col,
            var_name=var_name,
            raw_line=lines[lineno - 1],
        )
        for lineno, col, var_name in visitor.findings
    ]


def validate_paths(paths: Sequence[Path]) -> list[EnvReadFinding]:
    """Validate all Python files under the supplied paths."""
    findings: list[EnvReadFinding] = []
    for path in _iter_python_files(paths):
        findings.extend(validate_file(path))
    return findings


def _iter_python_files(paths: Sequence[Path]) -> Iterator[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from sorted(
                p for p in path.rglob("*.py") if "__pycache__" not in p.parts
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Block new os.environ/os.getenv reads outside the KEEP_ALLOWLIST. "
            "All config must flow through contract YAML or the overlay resolver "
            "(OMN-13566)."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[],
        help="Python files or directories to scan (pre-commit passes staged files).",
    )
    parser.add_argument(
        "--all",
        dest="scan_all",
        action="store_true",
        default=False,
        help="Scan the entire --src directory (CI mode).",
    )
    parser.add_argument(
        "--src",
        type=Path,
        default=Path("src"),
        help="Source root for --all mode (default: src/).",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    if args.scan_all:
        findings = validate_paths([args.src])
    elif args.paths:
        findings = validate_paths(args.paths)
    else:
        return 0

    if not findings:
        return 0

    sys.stderr.write(
        "no-new-os-environ: os.environ/os.getenv reads outside KEEP_ALLOWLIST found\n"
    )
    sys.stderr.write(
        "  All config must flow through contract YAML or the overlay resolver.\n"
        "  Add '# env-read-ok: <reason>' to suppress a structural bootstrap line,\n"
        "  or extend KEEP_ALLOWLIST in omnibase_core.validators.no_new_os_environ\n"
        "  via a CODEOWNERS-reviewed PR.\n\n"
    )
    for finding in findings:
        sys.stderr.write(f"  {finding.format()}\n")
        sys.stderr.write(f"    {finding.raw_line.strip()}\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
