# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-config compliance validator (OMN-10688).

Catches three anti-patterns in handler and script files:

1. **bare_env_read** — handler files calling os.environ.get() / os.environ[] /
   os.getenv() for variables NOT in INFRA_ALLOWLIST.  Config vars must be
   declared in the node's contract.yaml and resolved via the config layer.

2. **bus_bypass_import** — script files importing directly from
   nodes/*/handlers/  (bypasses the event bus; scripts must use the public
   node API).

3. **missing_contract_config** — handler files reading an env var that has no
   matching entry in the adjacent contract.yaml ``config`` or ``dependencies``
   section.

Usage::

    # Check src tree (returns non-zero on findings)
    python -m omnibase_core.validators.contract_config_compliance src/

    # Generate YAML allowlist of existing violations
    python -m omnibase_core.validators.contract_config_compliance \\
        --generate-allowlist src/ > allowlist.yaml

Suppression::

    Add  # contract-config-ok: <reason>  anywhere on a violating line to
    silence that specific finding.

INFRA_ALLOWLIST keys are connection bootstrap vars that intentionally live in
env rather than contract config (Kafka, Postgres, API credentials, etc.).
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import yaml  # ONEX_EXCLUDE: manual_yaml - validator reads adjacent contract.yaml files

from omnibase_core.models.validation.model_contract_config_finding import (
    ContractConfigFinding,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INFRA_ALLOWLIST: frozenset[str] = frozenset(
    {
        "KAFKA_BOOTSTRAP_SERVERS",
        "OMNI_HOME",
        "ONEX_STATE_DIR",
        "ONEX_STATE_ROOT",
        "OPENROUTER_API_KEY",
        "LINEAR_API_KEY",
        "GITHUB_TOKEN",
        "GH_PAT",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "LLM_GLM_API_KEY",
        "POSTGRES_PASSWORD",
        "MEMGRAPH_USER",
        "MEMGRAPH_PASSWORD",
        "GOOGLE_API_KEY",
    }
)

SUPPRESSION_MARKER = "contract-config-ok:"

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

_DEFAULT_SCAN_ROOT = Path("src")

# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _call_func_name(node: ast.Call) -> str | None:
    """Return dotted name of the called function, or None."""
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts: list[str] = []
        cur: ast.expr = func
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return None


def _str_arg(node: ast.Call) -> str | None:
    """Return the first string literal argument of a call, or None."""
    if node.args:
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    return None


def _subscript_str_key(node: ast.Subscript) -> str | None:
    """Return the string key of a subscript, or None."""
    sl = node.slice
    if isinstance(sl, ast.Constant) and isinstance(sl.value, str):
        return sl.value
    return None


def _module_of_import(node: ast.ImportFrom) -> str:
    return node.module or ""


# ---------------------------------------------------------------------------
# Rule checkers
# ---------------------------------------------------------------------------


def _check_bare_env_reads(
    path: Path,
    tree: ast.Module,
    lines: list[str],
) -> list[ContractConfigFinding]:
    """Rule bare_env_read: env reads outside INFRA_ALLOWLIST in handler files."""
    findings: list[ContractConfigFinding] = []

    class _Visitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            fname = _call_func_name(node)
            if fname in ("os.getenv", "os.environ.get"):
                key = _str_arg(node)
                if key and key not in INFRA_ALLOWLIST:
                    line_text = (
                        lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    )
                    if SUPPRESSION_MARKER not in line_text:
                        findings.append(
                            ContractConfigFinding(
                                path=path,
                                line=node.lineno,
                                column=node.col_offset,
                                rule="bare_env_read",
                                message=(
                                    f"bare env read of {key!r} — "
                                    "declare in contract.yaml config/dependencies instead"
                                ),
                            )
                        )
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if isinstance(node.value, ast.Attribute):
                if (
                    node.value.attr == "environ"
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == "os"
                ):
                    key = _subscript_str_key(node)
                    if key and key not in INFRA_ALLOWLIST:
                        line_text = (
                            lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        )
                        if SUPPRESSION_MARKER not in line_text:
                            findings.append(
                                ContractConfigFinding(
                                    path=path,
                                    line=node.lineno,
                                    column=node.col_offset,
                                    rule="bare_env_read",
                                    message=(
                                        f"bare env read of {key!r} — "
                                        "declare in contract.yaml config/dependencies instead"
                                    ),
                                )
                            )
            self.generic_visit(node)

    _Visitor().visit(tree)
    return findings


def _check_bus_bypass_imports(
    path: Path,
    tree: ast.Module,
    lines: list[str],
) -> list[ContractConfigFinding]:
    """Rule bus_bypass_import: scripts importing directly from nodes/*/handlers/."""
    findings: list[ContractConfigFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = _module_of_import(node)
            if "nodes" in mod and "handlers" in mod:
                line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                if SUPPRESSION_MARKER not in line_text:
                    findings.append(
                        ContractConfigFinding(
                            path=path,
                            line=node.lineno,
                            column=node.col_offset,
                            rule="bus_bypass_import",
                            message=(
                                f"direct handler import {mod!r} bypasses event bus — "
                                "use the node public API or contract topic instead"
                            ),
                        )
                    )
    return findings


def _extract_env_keys_from_tree(tree: ast.Module) -> set[str]:
    """Collect all string keys read from os.environ / os.getenv in this file."""
    keys: set[str] = set()

    class _KeyVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            fname = _call_func_name(node)
            if fname in ("os.getenv", "os.environ.get"):
                key = _str_arg(node)
                if key:
                    keys.add(key)
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if isinstance(node.value, ast.Attribute):
                if (
                    node.value.attr == "environ"
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == "os"
                ):
                    key = _subscript_str_key(node)
                    if key:
                        keys.add(key)
            self.generic_visit(node)

    _KeyVisitor().visit(tree)
    return keys


def _load_contract_env_keys(contract_path: Path) -> set[str]:
    """Extract declared env var names from a contract.yaml."""
    if not contract_path.exists():
        return set()
    try:
        # ONEX_EXCLUDE: manual_yaml - reading adjacent node contract for validation
        data = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001  # fallback-ok: malformed contract treated as empty
        return set()
    if not isinstance(data, dict):
        return set()
    keys: set[str] = set()
    # config section: flat key=value or env_var fields
    config = data.get("config", {})
    if isinstance(config, dict):
        for k, v in config.items():
            if k.endswith("_env_var") or k == "env_var":
                if isinstance(v, str):
                    keys.add(v)
            if isinstance(k, str) and k.isupper():
                keys.add(k)
    # dependencies section: type == "environment" entries
    deps = data.get("dependencies", [])
    if isinstance(deps, list):
        for dep in deps:
            if isinstance(dep, dict) and dep.get("type") == "environment":
                ev = dep.get("env_var")
                if isinstance(ev, str):
                    keys.add(ev)
    return keys


def _find_contract_yaml(handler_path: Path) -> Path | None:
    """Walk up from a handler file to find the nearest contract.yaml."""
    current = handler_path.parent
    for _ in range(6):
        candidate = current / "contract.yaml"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        # Stop searching once we've left the node tree
        if current.name in ("src", "nodes"):
            break
        current = parent
    return None


def _check_missing_contract_config(
    path: Path,
    tree: ast.Module,
    lines: list[str],
) -> list[ContractConfigFinding]:
    """Rule missing_contract_config: env reads in handlers not in contract.yaml."""
    env_keys = _extract_env_keys_from_tree(tree)
    uncovered = {k for k in env_keys if k not in INFRA_ALLOWLIST}
    if not uncovered:
        return []

    contract_path = _find_contract_yaml(path)
    contract_keys = _load_contract_env_keys(contract_path) if contract_path else set()

    missing = uncovered - contract_keys
    if not missing:
        return []

    findings: list[ContractConfigFinding] = []

    class _LineVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:
            fname = _call_func_name(node)
            if fname in ("os.getenv", "os.environ.get"):
                key = _str_arg(node)
                if key and key in missing:
                    line_text = (
                        lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                    )
                    if SUPPRESSION_MARKER not in line_text:
                        findings.append(
                            ContractConfigFinding(
                                path=path,
                                line=node.lineno,
                                column=node.col_offset,
                                rule="missing_contract_config",
                                message=(
                                    f"env var {key!r} read in handler but not declared "
                                    f"in contract.yaml "
                                    f"(nearest: {contract_path or 'not found'})"
                                ),
                            )
                        )
            self.generic_visit(node)

        def visit_Subscript(self, node: ast.Subscript) -> None:
            if isinstance(node.value, ast.Attribute):
                if (
                    node.value.attr == "environ"
                    and isinstance(node.value.value, ast.Name)
                    and node.value.value.id == "os"
                ):
                    key = _subscript_str_key(node)
                    if key and key in missing:
                        line_text = (
                            lines[node.lineno - 1] if node.lineno <= len(lines) else ""
                        )
                        if SUPPRESSION_MARKER not in line_text:
                            findings.append(
                                ContractConfigFinding(
                                    path=path,
                                    line=node.lineno,
                                    column=node.col_offset,
                                    rule="missing_contract_config",
                                    message=(
                                        f"env var {key!r} read in handler but not declared "
                                        f"in contract.yaml "
                                        f"(nearest: {contract_path or 'not found'})"
                                    ),
                                )
                            )
            self.generic_visit(node)

    _LineVisitor().visit(tree)
    return findings


# ---------------------------------------------------------------------------
# File-level dispatch
# ---------------------------------------------------------------------------


def _is_handler_file(path: Path) -> bool:
    """True if this file is inside a handlers/ directory."""
    return "handlers" in path.parts


def _is_script_file(path: Path) -> bool:
    """True if this file looks like a script (not inside src/, or in scripts/)."""
    parts = path.parts
    return "scripts" in parts or (
        "src" not in parts and "handlers" not in parts and "nodes" not in parts
    )


def _is_excluded(path: Path) -> bool:
    return any(part in _EXCLUDED_PATH_PARTS for part in path.parts)


def validate_file(
    path: Path, rules: frozenset[str] | None = None
) -> list[ContractConfigFinding]:
    """Validate one Python file; return findings list."""
    if _is_excluded(path):
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    lines = source.splitlines()
    active = rules or frozenset(
        {"bare_env_read", "bus_bypass_import", "missing_contract_config"}
    )
    findings: list[ContractConfigFinding] = []

    if "bare_env_read" in active and _is_handler_file(path):
        findings.extend(_check_bare_env_reads(path, tree, lines))

    if "bus_bypass_import" in active and _is_script_file(path):
        findings.extend(_check_bus_bypass_imports(path, tree, lines))

    if "missing_contract_config" in active and _is_handler_file(path):
        findings.extend(_check_missing_contract_config(path, tree, lines))

    return findings


def validate_paths(
    paths: list[Path], rules: frozenset[str] | None = None
) -> list[ContractConfigFinding]:
    """Validate all Python files under the given paths."""
    findings: list[ContractConfigFinding] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            findings.extend(validate_file(path, rules))
        elif path.is_dir():
            for py_file in sorted(path.rglob("*.py")):
                if "__pycache__" not in py_file.parts:
                    findings.extend(validate_file(py_file, rules))
    return findings


# ---------------------------------------------------------------------------
# --generate-allowlist
# ---------------------------------------------------------------------------


def generate_allowlist(findings: list[ContractConfigFinding]) -> str:
    """Render findings as a YAML allowlist for bootstrapping suppressions."""
    by_rule: dict[str, list[dict[str, object]]] = {}
    for f in findings:
        by_rule.setdefault(f.rule, []).append(
            {"path": str(f.path), "line": f.line, "message": f.message}
        )
    # ONEX_EXCLUDE: manual_yaml - generating allowlist YAML output
    return yaml.dump({"allowlist": by_rule}, default_flow_style=False, sort_keys=True)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

_VALIDATOR_NAME = "contract_config_compliance"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for contract-config compliance validator."""
    parser = argparse.ArgumentParser(
        description="Contract-config compliance validator (OMN-10688).",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[_DEFAULT_SCAN_ROOT],
        help="Python files or directories to scan.",
    )
    parser.add_argument(
        "--generate-allowlist",
        action="store_true",
        help="Output existing violations as YAML allowlist (stdout).",
    )
    parser.add_argument(
        "--rule",
        action="append",
        dest="rules",
        choices=["bare_env_read", "bus_bypass_import", "missing_contract_config"],
        help="Enable only specific rules (repeatable; default: all rules).",
    )
    args = parser.parse_args(argv)

    active_rules = frozenset(args.rules) if args.rules else None
    findings = validate_paths(args.paths, active_rules)

    if args.generate_allowlist:
        sys.stdout.write(generate_allowlist(findings))
        return 0

    if not findings:
        return 0

    sys.stderr.write(f"{_VALIDATOR_NAME}: {len(findings)} finding(s):\n")
    for f in findings:
        sys.stderr.write(f"  {f.format()}\n")
    sys.stderr.write(
        "\nDeclare config vars in contract.yaml and resolve via the config layer.\n"
        "Suppress individual lines with:  # contract-config-ok: <reason>\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())  # error-ok: CLI entry point requires SystemExit
