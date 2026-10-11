# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI of the imperative contract guard (OMN-20918): the EFFECT boundary of its handlers.

Ported from onex_change_control ``scripts.check_imperative_contracts`` at 725d2967 for
OCC retirement step S8: reads each repository tree and its allowlist, hands the
sources to :class:`HandlerImperativeContractGuard`, renders the source's text,
Markdown and JSON reports, and exits non-zero on a blocking LIVE violation.

Beyond the source, ``--allowlist-path`` names the repository's own allowlist (relative
to ``--repo-root``) and ``--ratchet-base-ref`` refuses an allowlist that gains a path
against the merge base with that ref (:class:`HandlerImperativeAllowlistRatchet`).

Usage::

    uv run check-imperative-contracts --repo-root . \\
        --allowlist-path imperative-contract-allowlist.yaml \\
        --scan-freestanding --ratchet-base-ref origin/dev

Exit 0 = clean, 1 = a blocking violation or a refused ratchet, 2 = unsupported arguments.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_arch_handler_contract_compliance import (
    _find_node_dirs,
    _infer_repo_name,
    _read_text_if_present,
)
from omnibase_core.handlers.handler_imperative_allowlist_ratchet import (
    HandlerImperativeAllowlistRatchet,
    allowlisted_paths,
)
from omnibase_core.handlers.handler_imperative_contract_guard import (
    HandlerImperativeContractGuard,
)
from omnibase_core.models.nodes.handler_contract_compliance.model_compliance_node_source import (
    ModelComplianceNodeSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_allowlist_ratchet_input import (
    ModelAllowlistRatchetInput,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_contract_source import (
    ModelGuardContractSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_guard_module_source import (
    ModelGuardModuleSource,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_imperative_contract_guard_input import (
    ModelImperativeContractGuardInput,
)
from omnibase_core.models.nodes.imperative_contract_guard.model_imperative_repo_summary import (
    ModelImperativeRepoSummary,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile

_SKIP_REPO_DIRS = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".repowise",
        ".ruff_cache",
        ".venv",
        "__pycache__",
        "node_modules",
        "omni_worktrees",
    }
)

_ALLOWLIST_FILENAME = "arch-handler-contract-compliance-allowlist.yaml"


def discover_repo_roots(workspace_root: Path) -> list[Path]:
    """Return first-level git repositories under ``workspace_root``."""
    repos: list[Path] = []
    for child in sorted(workspace_root.iterdir(), key=lambda path: path.name):
        if child.name in _SKIP_REPO_DIRS or child.name.startswith("."):
            continue
        if child.is_dir() and (child / ".git").exists():
            repos.append(child)
    return repos


def _resolve_allowlist_path(
    *,
    repo_root: Path,
    repo_label: str,
    repo_name: str,
    allowlists_dir: Path | None,
) -> Path | None:
    """Resolve the allowlist path for a repo.

    An explicit central allowlists directory wins so workspace CI can use a single
    controlled baseline. Repo-local allowlists remain the default for per-repo CI jobs
    that do not pass ``--allowlists-dir``.
    """
    if allowlists_dir is None:
        repo_local = repo_root / _ALLOWLIST_FILENAME
        return repo_local if repo_local.exists() else None
    for name in (repo_label, repo_name):
        candidate = allowlists_dir / f"{name}.yaml"
        if candidate.exists():
            return candidate
    repo_local = repo_root / _ALLOWLIST_FILENAME
    return repo_local if repo_local.exists() else None


def _rel(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _read_node(repo_root: Path, node_dir: Path) -> ModelComplianceNodeSource:
    """Read one node directory; paths are relative to the repository root."""
    handler_files = sorted(
        f
        for f in (node_dir / "handlers").rglob("*.py")
        if f.name != "__init__.py" and not f.name.startswith("_")
    )
    return ModelComplianceNodeSource(
        node_dir=_rel(repo_root, node_dir),
        contract_yaml=_read_text_if_present(node_dir / "contract.yaml"),
        node_py=_read_text_if_present(node_dir / "node.py"),
        handlers=[
            ModelSourceFile(
                path=_rel(repo_root, handler_file),
                source=handler_file.read_text(encoding="utf-8"),
            )
            for handler_file in handler_files
        ],
    )


def _read_modules(repo_root: Path) -> list[ModelGuardModuleSource]:
    """Read every ``src/**/*.py`` module outside ``__pycache__``."""
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return []
    return [
        ModelGuardModuleSource(
            path=_rel(repo_root, path), source=path.read_text(encoding="utf-8")
        )
        for path in sorted(src_dir.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def _read_contracts(repo_root: Path) -> list[ModelGuardContractSource]:
    """Read every ``src/**/contract.yaml`` with whether a ``node.py`` sits beside it."""
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return []
    return [
        ModelGuardContractSource(
            path=_rel(repo_root, path),
            text=path.read_text(encoding="utf-8"),
            has_node_py=(path.parent / "node.py").exists(),
        )
        for path in sorted(src_dir.rglob("contract.yaml"))
    ]


def scan_repo(
    repo_root: Path,
    *,
    allowlists_dir: Path | None = None,
    allowlist_path: Path | None = None,
    scan_freestanding: bool = False,
) -> ModelImperativeRepoSummary:
    """Scan a repository and return its imperative-contract summary."""
    repo_root = repo_root.resolve()
    repo_name = _infer_repo_name(repo_root)
    repo_label = repo_root.name
    resolved = (
        allowlist_path
        if allowlist_path is not None
        else _resolve_allowlist_path(
            repo_root=repo_root,
            repo_label=repo_label,
            repo_name=repo_name,
            allowlists_dir=allowlists_dir,
        )
    )
    paths = (
        allowlisted_paths(_read_text_if_present(resolved))
        if resolved is not None
        else []
    )
    report = HandlerImperativeContractGuard().handle(
        ModelImperativeContractGuardInput(
            repo=repo_name,
            nodes=[_read_node(repo_root, d) for d in _find_node_dirs(repo_root)],
            allowlisted_paths=paths,
            scan_freestanding=scan_freestanding,
            modules=_read_modules(repo_root) if scan_freestanding else [],
            contracts=_read_contracts(repo_root) if scan_freestanding else [],
            pyproject_text=_read_text_if_present(repo_root / "pyproject.toml"),
        )
    )
    return ModelImperativeRepoSummary(
        repo=repo_label,
        repo_root=str(repo_root),
        allowlist_path=str(resolved) if resolved is not None else None,
        report=report,
    )


def scan_repos(
    repo_roots: list[Path],
    *,
    allowlists_dir: Path | None = None,
    allowlist_path: Path | None = None,
    scan_freestanding: bool = False,
) -> list[ModelImperativeRepoSummary]:
    """Scan multiple repositories in deterministic order."""
    return [
        scan_repo(
            repo_root=repo_root,
            allowlists_dir=allowlists_dir,
            allowlist_path=allowlist_path,
            scan_freestanding=scan_freestanding,
        )
        for repo_root in sorted(repo_roots, key=lambda path: path.name)
    ]


def render_text_report(
    summaries: list[ModelImperativeRepoSummary],
) -> str:
    """Render a human-readable table plus unbaselined violation details."""
    lines = [
        "Imperative contract guard",
        "",
        (
            f"{'repo':28} {'nodes':>5} {'handlers':>8} {'clean':>6} "
            f"{'baseline':>8} {'live':>5} {'nonlive':>7} allowlist"
        ),
        "-" * 102,
    ]
    for summary in summaries:
        report = summary.report
        allowlist = summary.allowlist_path or "(none)"
        lines.append(
            f"{summary.repo:28} {report.node_count:5} "
            f"{summary.handler_count:8} {report.compliant_count:6} "
            f"{report.allowlisted_count:8} {report.new_violation_count:5} "
            f"{report.non_live_violation_count:7} "
            f"{allowlist}"
        )

    new_results = [r for s in summaries for r in s.report.blocking_results]
    if new_results:
        lines.extend(["", "Blocking LIVE imperative violations:"])
        for result in new_results:
            lines.append(
                f"- {result.handler_path}: {result.verdict.value} "
                f"({result.reachability.value})"
            )
            lines.extend(f"  - {detail}" for detail in result.violation_details)

    freestanding = [r for s in summaries for r in s.report.blocking_freestanding]
    if freestanding:
        lines.extend(["", "Blocking LIVE freestanding imperative violations:"])
        for fs_result in freestanding:
            lines.append(
                f"- {fs_result.module_path}: {fs_result.verdict.value} "
                f"({fs_result.reachability.value})"
            )
            lines.extend(
                f"  - L{finding.line} [{finding.reachability.value}] {finding.detail}"
                for finding in fs_result.active_findings
            )

    non_live = [r for s in summaries for r in s.report.non_live_results]
    non_live_freestanding = [
        r for s in summaries for r in s.report.non_live_freestanding
    ]
    if non_live or non_live_freestanding:
        lines.extend(["", "Reported non-live imperative smells:"])
        lines.extend(
            f"- {r.handler_path}: {r.verdict.value} ({r.reachability.value})"
            for r in non_live
        )
        lines.extend(
            f"- {r.module_path}: {r.verdict.value} ({r.reachability.value})"
            for r in non_live_freestanding
        )
    return "\n".join(lines)


def render_markdown_report(
    summaries: list[ModelImperativeRepoSummary],
) -> str:
    """Render a Markdown report suitable for durable sweep evidence."""
    lines = [
        "# Imperative Contract Guard Sweep",
        "",
        (
            "| Repo | Nodes | Handlers | Clean | Baselined | Live blockers "
            "| Non-live reported | Allowlist |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for summary in summaries:
        report = summary.report
        allowlist = summary.allowlist_path or "(none)"
        lines.append(
            f"| `{summary.repo}` | {report.node_count} | {summary.handler_count} "
            f"| {report.compliant_count} | {report.allowlisted_count} "
            f"| {report.new_violation_count} | {report.non_live_violation_count} "
            f"| `{allowlist}` |"
        )

    lines.extend(["", "## Blocking LIVE Violations"])
    new_results = [r for s in summaries for r in s.report.blocking_results]
    if not new_results:
        lines.append("")
        lines.append("None.")
    for result in new_results:
        lines.append("")
        lines.append(f"### `{result.handler_path}`")
        lines.append("")
        lines.append(f"- Verdict: `{result.verdict.value}`")
        lines.append(f"- Reachability: `{result.reachability.value}`")
        lines.extend(f"- {detail}" for detail in result.violation_details)

    freestanding = [r for s in summaries for r in s.report.blocking_freestanding]
    if any(s.report.freestanding_scanned for s in summaries):
        lines.extend(["", "## Blocking LIVE Freestanding Violations"])
        if not freestanding:
            lines.extend(["", "None."])
        for fs_result in freestanding:
            lines.append("")
            lines.append(f"### `{fs_result.module_path}`")
            lines.append("")
            lines.append(f"- Verdict: `{fs_result.verdict.value}`")
            lines.append(f"- Reachability: `{fs_result.reachability.value}`")
            lines.extend(
                f"- L{finding.line} [{finding.reachability.value}] {finding.detail}"
                for finding in fs_result.active_findings
            )

    non_live = [r for s in summaries for r in s.report.non_live_results]
    non_live_freestanding = [
        r for s in summaries for r in s.report.non_live_freestanding
    ]
    lines.extend(["", "## Reported Non-live Smells"])
    if not non_live and not non_live_freestanding:
        lines.extend(["", "None."])
    for result in non_live:
        lines.append("")
        lines.append(f"### `{result.handler_path}`")
        lines.append(f"- Verdict: `{result.verdict.value}`")
        lines.append(f"- Reachability: `{result.reachability.value}`")
    for fs_result in non_live_freestanding:
        lines.append("")
        lines.append(f"### `{fs_result.module_path}`")
        lines.append(f"- Verdict: `{fs_result.verdict.value}`")
        lines.append(f"- Reachability: `{fs_result.reachability.value}`")
    return "\n".join(lines) + "\n"


def _git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _base_allowlist_text(
    repo_root: Path, allowlist_path: Path, base_ref: str
) -> str | None:
    """Return the allowlist text at the merge base with ``base_ref``; None when absent there."""
    merge_base = _git(repo_root, "merge-base", "HEAD", base_ref)
    if merge_base.returncode != 0:
        raise ModelOnexError(
            message=(
                f"ratchet base ref {base_ref!r} has no merge base with HEAD: "
                f"{merge_base.stderr.strip()}"
            ),
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
        )
    rel = allowlist_path.resolve().relative_to(repo_root.resolve()).as_posix()
    base = merge_base.stdout.strip()
    listed = _git(repo_root, "ls-tree", "--name-only", base, "--", rel)
    if listed.returncode != 0:
        raise ModelOnexError(
            message=f"cannot list {rel!r} at {base}: {listed.stderr.strip()}",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
        )
    if not listed.stdout.strip():
        return None
    shown = _git(repo_root, "show", f"{base}:{rel}")
    if shown.returncode != 0:
        raise ModelOnexError(
            message=f"cannot read {rel!r} at {base}: {shown.stderr.strip()}",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
        )
    return shown.stdout


def run_ratchet(repo_root: Path, allowlist_path: Path, base_ref: str) -> int:
    """Refuse an allowlist that gains a path against the merge base; 0 admits, 1 refuses."""
    report = HandlerImperativeAllowlistRatchet().handle(
        ModelAllowlistRatchetInput(
            base_text=_base_allowlist_text(repo_root, allowlist_path, base_ref),
            head_text=_read_text_if_present(allowlist_path),
        )
    )
    if report.bootstrap:
        sys.stdout.write(
            f"Allowlist ratchet: {allowlist_path.name} is absent at the merge base "
            f"with {base_ref}; first landing admitted as the baseline "
            f"({len(allowlisted_paths(_read_text_if_present(allowlist_path)))} paths)\n"
        )
        return 0
    if report.added:
        sys.stdout.write(
            f"Allowlist ratchet REFUSED: {allowlist_path.name} gains "
            f"{len(report.added)} path(s) against the merge base with {base_ref}; "
            "the allowlist only shrinks:\n"
        )
        for path in report.added:
            sys.stdout.write(f"  + {path}\n")
        return 1
    sys.stdout.write(
        f"Allowlist ratchet: {allowlist_path.name} gains no path against the merge "
        f"base with {base_ref} ({len(report.removed)} removed)\n"
    )
    return 0


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check-imperative-contracts",
        description="Fail on unbaselined imperative ONEX node/handler code.",
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="Workspace root containing first-level git repositories.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        action="append",
        default=[],
        help="Repository root to scan. May be passed multiple times.",
    )
    parser.add_argument(
        "--allowlists-dir",
        type=Path,
        help="Directory containing <repo>.yaml handler compliance allowlists.",
    )
    parser.add_argument(
        "--allowlist-path",
        type=Path,
        help="The repository's own allowlist (relative to --repo-root); one --repo-root only.",
    )
    parser.add_argument(
        "--ratchet-base-ref",
        help="Refuse the allowlist if it gains a path against the merge base with this ref.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of text.",
    )
    parser.add_argument(
        "--markdown-report",
        type=Path,
        help="Write a Markdown sweep report to this path.",
    )
    parser.add_argument(
        "--no-fail",
        action="store_true",
        help="Report findings but exit zero.",
    )
    parser.add_argument(
        "--scan-freestanding",
        action="store_true",
        help=(
            "Also audit freestanding src/ modules (everything outside "
            "node_*/handlers/) for imperative IO: raw HTTP/Kafka/DB, hardcoded "
            "inference params, topics, LAN IPs, and subprocess network ops."
        ),
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the exit code."""
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_roots = list(args.repo_root)
    if args.workspace_root is not None:
        repo_roots.extend(discover_repo_roots(args.workspace_root))
    if not repo_roots:
        sys.stderr.write("ERROR: pass --workspace-root or at least one --repo-root\n")
        return 2
    if (args.allowlist_path or args.ratchet_base_ref) and len(repo_roots) != 1:
        sys.stderr.write(
            "ERROR: --allowlist-path and --ratchet-base-ref take exactly one repository\n"
        )
        return 2
    allowlist_path: Path | None = None
    if args.allowlist_path is not None:
        allowlist_path = (
            args.allowlist_path
            if args.allowlist_path.is_absolute()
            else repo_roots[0] / args.allowlist_path
        )

    summaries = scan_repos(
        repo_roots=repo_roots,
        allowlists_dir=args.allowlists_dir,
        allowlist_path=allowlist_path,
        scan_freestanding=args.scan_freestanding,
    )
    if args.markdown_report is not None:
        args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_report.write_text(render_markdown_report(summaries))

    if args.json:
        sys.stdout.write(
            json.dumps([summary.to_json() for summary in summaries], indent=2) + "\n"
        )
    else:
        sys.stdout.write(render_text_report(summaries) + "\n")

    ratchet_exit = 0
    if args.ratchet_base_ref is not None:
        resolved = summaries[0].allowlist_path
        if resolved is not None:
            ratchet_exit = run_ratchet(
                repo_roots[0], Path(resolved), args.ratchet_base_ref
            )

    if args.no_fail:
        return 0
    blocking = any(summary.report.new_violation_count for summary in summaries)
    return 1 if blocking or ratchet_exit else 0


if __name__ == "__main__":
    sys.exit(main())
