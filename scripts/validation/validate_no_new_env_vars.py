#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Validator: no new os.environ / os.getenv additions (OMN-11186).

All config must flow through contract YAML or Infisical — not bare env var reads.
This hook flags any new os.environ[...], os.environ.get(...), or os.getenv(...)
call that is not in the established allowlist.

Bypass: add `# env-var-ok` on the line to suppress a specific instance.

Allowlisted env vars are structurally required cross-machine bootstrap values
(OMNI_HOME, PATH, CI, etc.) or pre-existing reads grandfathered at activation.
New env vars outside the allowlist must go through contract YAML review.

Usage:
    python scripts/validation/validate_no_new_env_vars.py [files...]

Exit codes:
    0 - No violations
    1 - Violations found
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Structurally required bootstrap env vars (zero-friction allowlist)
# ---------------------------------------------------------------------------
_BOOTSTRAP_ALLOWLIST: frozenset[str] = frozenset(
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
        # CI environment detection
        "CI",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "CI_RUNNER_TYPE",
        "JENKINS_URL",
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
        # ONEX event bus config (existing reads grandfathered at OMN-11186 activation)
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
        # Postgres doctor checks (pre-existing; infra diagnostic tooling)
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        # Namespacing / allowed namespace overrides
        "OMNIBASE_ALLOWED_NAMESPACES",
        # Linear / external API (doctor checks only)
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
        # Used in scripts/validation (these scripts are themselves tooling)
        "DETERMINISTIC_SKILL_ROOT",
        "ZONE_DIFF_FILTER_FAKE_DIFF",
        # PYTHONPATH (tooling launchers)
        "PYTHONPATH",
    }
)

# ---------------------------------------------------------------------------
# Patterns we scan for (line-level, no AST needed)
# ---------------------------------------------------------------------------
_ENV_VAR_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"os\.environ\["),
    re.compile(r"os\.environ\.get\("),
    re.compile(r"os\.getenv\("),
)

# Extract the env var name from a line (best-effort; handles quoted keys)
_NAME_EXTRACTOR = re.compile(
    r'os\.(?:environ\.get|environ|getenv)\s*[\[(]\s*["\']([^"\']+)["\']'
)

# ---------------------------------------------------------------------------
# Skip rules
# ---------------------------------------------------------------------------


def _is_test_file(path: Path) -> bool:
    parts = path.parts
    return "tests" in parts


def _is_tooling_or_demo(path: Path) -> bool:
    """Skip validator scripts and demo/example code."""
    parts = path.parts
    return "scripts" in parts or "examples" in parts


def _line_has_bypass(line: str) -> bool:
    return "# env-var-ok" in line


def _is_comment_line(line: str) -> bool:
    return line.lstrip().startswith("#")


def _should_skip_path(path: Path) -> bool:
    return (
        not path.exists()
        or path.suffix != ".py"
        or _is_test_file(path)
        or _is_tooling_or_demo(path)
    )


def _read_python_file(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _opening_multiline_delimiter(stripped_line: str) -> str | None:
    for delimiter in ('"""', "'''"):
        if delimiter in stripped_line and stripped_line.count(delimiter) % 2 == 1:
            return delimiter
    return None


def _iter_scannable_lines(content: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    in_multiline_string = False
    multiline_delim = ""

    for lineno, line in enumerate(content.splitlines(), 1):
        if in_multiline_string:
            if multiline_delim in line:
                in_multiline_string = False
            continue

        delimiter = _opening_multiline_delimiter(line.lstrip())
        if delimiter is not None:
            in_multiline_string = True
            multiline_delim = delimiter
            continue

        lines.append((lineno, line))

    return lines


def _extract_disallowed_env_name(line: str) -> str | None:
    if _line_has_bypass(line) or _is_comment_line(line):
        return None

    if not any(pattern.search(line) for pattern in _ENV_VAR_PATTERNS):
        return None

    name_match = _NAME_EXTRACTOR.search(line)
    if name_match is None:
        return None

    var_name = name_match.group(1)
    if var_name in _BOOTSTRAP_ALLOWLIST:
        return None

    return var_name


# ---------------------------------------------------------------------------
# Core check
# ---------------------------------------------------------------------------


def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_number, raw_line, extracted_var_name) violations."""
    if _should_skip_path(path):
        return []

    content = _read_python_file(path)
    if content is None:
        return []

    violations: list[tuple[int, str, str]] = []
    for lineno, line in _iter_scannable_lines(content):
        var_name = _extract_disallowed_env_name(line)
        if var_name is not None:
            violations.append((lineno, line.rstrip(), var_name))

    return violations


def main() -> int:
    files = [Path(f) for f in sys.argv[1:]]
    if not files:
        return 0

    all_violations: dict[str, list[tuple[int, str, str]]] = {}

    for f in files:
        violations = check_file(f)
        if violations:
            all_violations[str(f)] = violations

    if not all_violations:
        return 0

    print("no-new-env-vars: new os.environ/os.getenv calls found outside allowlist")
    print(
        "  All config must flow through contract YAML or Infisical."
        " Add '# env-var-ok' to suppress if this is a structural bootstrap var,"
        " or expand _BOOTSTRAP_ALLOWLIST in validate_no_new_env_vars.py via PR review."
    )
    print()

    for file_path, violations in sorted(all_violations.items()):
        for lineno, line, var_name in violations:
            var_info = f" ({var_name!r})" if var_name else " (dynamic key)"
            print(f"  {file_path}:{lineno}{var_info}")
            print(f"    {line.strip()}")

    return 1


if __name__ == "__main__":
    sys.exit(main())
