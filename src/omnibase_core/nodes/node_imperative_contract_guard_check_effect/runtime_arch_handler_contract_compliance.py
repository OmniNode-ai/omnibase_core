# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the handler contract compliance scan (OMN-20074).

``main`` reads the repository tree and the allowlist, runs
``HandlerArchHandlerContractCompliance`` over the node sources and prints the
source's summary lines.

Usage::

    python -m omnibase_core.nodes.node_imperative_contract_guard_check_effect.runtime_arch_handler_contract_compliance \\
        --repo-root . --allowlist-path arch-handler-contract-compliance-allowlist.yaml

    # Generate an initial allowlist from the current violations
    python -m omnibase_core.nodes.node_imperative_contract_guard_check_effect.runtime_arch_handler_contract_compliance \\
        --repo-root . --generate-allowlist

Exit code 0 = clean (or no node directories found). Exit code 1 = a handler has a
violation that is not allowlisted. Exit code 2 = unsupported arguments.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import yaml

from omnibase_core.models.governance.model_handler_compliance_result import (
    ModelHandlerComplianceResult,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_compliance_node_source import (
    ModelComplianceNodeSource,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_handler_contract_compliance_input import (
    ModelHandlerContractComplianceInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.nodes.node_imperative_contract_guard_check_effect.handler_arch_handler_contract_compliance import (
    HandlerArchHandlerContractCompliance,
)

# --- Repository tree reads (the EFFECT boundary of ``main``) ---


def _find_node_dirs(repo_root: Path) -> list[Path]:
    """Find all node directories (``node_*`` with a ``handlers/`` directory)."""
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return []

    node_dirs: list[Path] = []
    for nodes_dir in src_dir.rglob("nodes"):
        if not nodes_dir.is_dir():
            continue
        for child in sorted(nodes_dir.iterdir()):
            if child.is_dir() and child.name.startswith("node_"):
                handlers_dir = child / "handlers"
                if handlers_dir.exists():
                    node_dirs.append(child)

    return node_dirs


def _infer_repo_name(repo_root: Path) -> str:
    """Infer the repository name from the first package directory under ``src``."""
    src_dir = repo_root / "src"
    if src_dir.exists():
        for child in src_dir.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                return child.name
    return repo_root.name


def _read_text_if_present(path: Path) -> str | None:
    """Read a UTF-8 file, or None when it does not exist."""
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _read_node(node_dir: Path) -> ModelComplianceNodeSource:
    """Read the contract, node.py and handler modules of one node directory."""
    handler_files = sorted(
        f
        for f in (node_dir / "handlers").rglob("*.py")
        if f.name != "__init__.py" and not f.name.startswith("_")
    )
    return ModelComplianceNodeSource(
        node_dir=node_dir.as_posix(),
        contract_yaml=_read_text_if_present(node_dir / "contract.yaml"),
        node_py=_read_text_if_present(node_dir / "node.py"),
        handlers=[
            ModelSourceFile(
                path=handler_file.as_posix(),
                source=handler_file.read_text(encoding="utf-8"),
            )
            for handler_file in handler_files
        ],
    )


def _load_allowlist(allowlist_path: Path) -> list[str]:
    """Load allowlist YAML, returning the allowlisted handler paths."""
    if not allowlist_path.exists():
        return []

    with allowlist_path.open(encoding="utf-8") as f:
        data = yaml.load(
            f, Loader=yaml.SafeLoader
        )  # SafeLoader, as the source's safe_load

    if not isinstance(data, dict):
        return []

    paths: list[str] = []
    for entry in data.get("allowlisted_handlers", []) or []:
        path = entry.get("path", "")
        if path:
            paths.append(path)
    return paths


def _write(msg: str) -> None:
    """Write a line to stdout (CI output)."""
    sys.stdout.write(msg + "\n")


def _output_allowlist(results: list[ModelHandlerComplianceResult]) -> None:
    """Output current violations as allowlist YAML."""
    entries = [
        {
            "path": r.handler_path,
            "violations": [str(v) for v in r.violations],
            "ticket": "# migration pending",
        }
        for r in results
        if r.violations
    ]
    _write(
        yaml.dump(
            {"allowlisted_handlers": entries}, default_flow_style=False, sort_keys=False
        )
    )


def run_scan(
    repo_root: Path,
    allowlist_path: Path | None = None,
    *,
    generate_allowlist: bool = False,
    output_json: bool = False,
) -> int:
    """Run the handler contract compliance scan; 0 if clean, 1 if violations found."""
    repo_name = _infer_repo_name(repo_root)
    node_dirs = _find_node_dirs(repo_root)

    if not node_dirs:
        _write(f"No node directories found in {repo_root}")
        return 0

    allowlisted_paths = _load_allowlist(allowlist_path) if allowlist_path else []
    report = HandlerArchHandlerContractCompliance().handle(
        ModelHandlerContractComplianceInput(
            repo=repo_name,
            nodes=[_read_node(node_dir) for node_dir in node_dirs],
            allowlisted_paths=allowlisted_paths,
        )
    )

    if generate_allowlist:
        _output_allowlist(report.results)
        return 0

    if output_json:
        _write(
            json.dumps([r.model_dump(mode="json") for r in report.results], indent=2)
        )

    new_violations = report.new_violations
    _write(f"\n=== Handler Contract Compliance: {repo_name} ===")
    _write(f"Total handlers: {report.total}")
    _write(f"Compliant: {report.compliant_count}")
    _write(f"Allowlisted: {report.allowlisted_count}")
    _write(f"New violations: {len(new_violations)}")

    if new_violations:
        _write("\n--- New violations (not allowlisted) ---")
        for r in new_violations:
            _write(f"\n  {r.handler_path}")
            _write(f"    Verdict: {r.verdict}")
            for detail in r.violation_details:
                _write(f"    - {detail}")
        return 1

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the exit code."""
    parser = argparse.ArgumentParser(
        description="Handler contract compliance validator"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
        help="Repository root path",
    )
    parser.add_argument(
        "--allowlist-path",
        type=Path,
        default=None,
        help="Path to allowlist YAML",
    )
    parser.add_argument(
        "--generate-allowlist",
        action="store_true",
        help="Output current violations as allowlist",
    )
    parser.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Output JSON report",
    )

    args = parser.parse_args(sys.argv[1:] if argv is None else list(argv))
    return run_scan(
        repo_root=args.repo_root,
        allowlist_path=args.allowlist_path,
        generate_allowlist=args.generate_allowlist,
        output_json=args.output_json,
    )


if __name__ == "__main__":
    sys.exit(main())
