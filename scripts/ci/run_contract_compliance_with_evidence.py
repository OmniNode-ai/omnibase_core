# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Fail closed before invoking the pinned OCC contract-compliance runner."""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path


def _extract_ticket_id(*, checker_dir: Path, pr_number: int, repo: str) -> str | None:
    """Use the pinned runner's own ticket precedence for preflight and execution."""
    source_root = checker_dir / "src"
    if not source_root.is_dir():
        raise RuntimeError(f"Pinned checker source is unavailable: {source_root}")
    sys.path.insert(0, str(source_root))
    try:
        checker = importlib.import_module(
            "onex_change_control.scripts.contract_compliance_check"
        )
        extract = getattr(checker, "_extract_ticket_id", None)
        if not callable(extract):
            raise RuntimeError("Pinned checker does not expose its ticket resolver")
        result = extract(pr_number, repo)
    finally:
        sys.path.pop(0)
    return result if isinstance(result, str) else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--checker-dir", required=True, type=Path)
    parser.add_argument("--evidence-contracts-dir", required=True, type=Path)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--legacy-allowlist", required=True, type=Path)
    args = parser.parse_args()

    try:
        ticket_id = _extract_ticket_id(
            checker_dir=args.checker_dir, pr_number=args.pr, repo=args.repo
        )
    except (ImportError, OSError, RuntimeError) as exc:
        sys.stderr.write(
            f"::error::Contract Compliance ticket resolution failed: {exc}\n"
        )
        return 1
    if ticket_id is None:
        sys.stderr.write(
            "::error::Contract Compliance could not resolve an OMN ticket using the pinned "
            "runner's title, branch, body precedence.\n"
        )
        return 1

    contract_path = args.evidence_contracts_dir / f"{ticket_id}.yaml"
    if not contract_path.is_file():
        sys.stderr.write(
            "::error::Contract Compliance evidence data lacks the resolved ticket contract: "
            f"{contract_path}\n"
        )
        return 1

    runner = args.checker_dir / "scripts" / "ci" / "run_contract_compliance_check.py"
    if not runner.is_file():
        sys.stderr.write(
            f"::error::Pinned contract-compliance runner is unavailable: {runner}\n"
        )
        return 1
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(runner),
            "--pr",
            str(args.pr),
            "--repo",
            args.repo,
            "--contracts-dir",
            str(args.evidence_contracts_dir),
            "--workspace",
            str(args.workspace),
            "--legacy-allowlist",
            str(args.legacy_allowlist),
        ],
        cwd=args.checker_dir,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
