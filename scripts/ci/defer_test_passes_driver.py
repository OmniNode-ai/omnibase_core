# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Run the pinned OCC compliance runner with ``test_passes`` deferred (OMN-18157).

The pinned runner judges a ``test_passes`` item with ``gh pr checks`` and treats
every check that is not SUCCESS, SKIPPED or NEUTRAL as a failure. Inside the
Contract Compliance Check job that set always includes the job itself, still
running, so such an item can never pass there. This driver runs the pinned
runner's own ``main()`` unchanged except for that one check type: each
``test_passes`` item is reported WARN and written to ``--deferred-record``, and
CI Summary evaluates the record once every other check has a verdict
(``scripts/ci/deferred_test_passes_gate.py``).

It runs inside the pinned checker's environment (``uv run`` from that checkout),
so every other check type executes exactly as the pinned runner executes it.

Usage::

    python defer_test_passes_driver.py --deferred-record <path> -- <runner args>
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from types import ModuleType

_CHECKER_MODULE = "onex_change_control.scripts.contract_compliance_check"
_DEFERRED_DETAIL = (
    "DEFERRED to CI Summary (OMN-18157): judged there once every other check "
    "on the PR has a verdict, because in this job the check set includes this "
    "job itself, still running."
)


def install_deferral(checker: ModuleType, deferred: list[dict[str, object]]) -> None:
    """Replace the pinned runner's ``test_passes`` entry with a recording deferral."""
    runners = getattr(checker, "_CHECK_RUNNERS", None)
    if not isinstance(runners, dict) or "test_passes" not in runners:
        raise RuntimeError(
            "pinned checker has no _CHECK_RUNNERS['test_passes'] entry to defer"
        )
    warn = getattr(checker, "_RESULT_WARN", None)
    if not isinstance(warn, str):
        raise RuntimeError("pinned checker has no _RESULT_WARN result constant")

    def _defer_test_passes(
        check_value: object, _workspace: Path, pr_number: int, repo: str
    ) -> tuple[str, str]:
        deferred.append(
            {"pr_number": pr_number, "repo": repo, "check_value": str(check_value)}
        )
        return warn, _DEFERRED_DETAIL

    runners["test_passes"] = _defer_test_passes


def main(argv: list[str] | None = None) -> int:
    raw = sys.argv[1:] if argv is None else argv
    if "--" not in raw:
        sys.stderr.write("::error::usage: --deferred-record <path> -- <runner args>\n")
        return 1
    split = raw.index("--")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deferred-record", required=True, type=Path)
    args = parser.parse_args(raw[:split])

    # This file lives in the product's scripts/ci; keep that directory from
    # shadowing any module the pinned checker imports.
    own_dir = str(Path(__file__).resolve().parent)
    sys.path[:] = [entry for entry in sys.path if entry != own_dir]

    deferred: list[dict[str, object]] = []
    try:
        checker = importlib.import_module(_CHECKER_MODULE)
        install_deferral(checker, deferred)
    except (ImportError, RuntimeError) as exc:
        sys.stderr.write(f"::error::Cannot defer test_passes items: {exc}\n")
        return 1

    sys.argv = ["run_contract_compliance_check.py", *raw[split + 1 :]]
    code = checker.main()
    args.deferred_record.parent.mkdir(parents=True, exist_ok=True)
    args.deferred_record.write_text(
        json.dumps({"schema": 1, "deferred": deferred}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(  # noqa: T201 - CI log line
        f"[INFO] {len(deferred)} test_passes item(s) deferred to CI Summary "
        f"(record: {args.deferred_record})",
        flush=True,
    )
    return int(code)


if __name__ == "__main__":
    raise SystemExit(main())
