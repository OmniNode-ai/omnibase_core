# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Legacy release-identity CLI plus report output and repository selection.

All reads and Git invocations belong to the paired gather EFFECT. Reports are
persisted exclusively by the validation-report write EFFECT. The COMPUTE node
keeps core's wheel-version messages and Git selection semantics. Configuration
errors retain exit 2; unreadable inputs exit 1.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.models.nodes.release_identity_check.model_release_identity_gather_input import (
    ModelReleaseIdentityGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_release_identity_check_compute.handler import (
    NodeReleaseIdentityCheckCompute,
)
from omnibase_core.nodes.node_release_identity_check_compute.release_identity_rules import (
    VALIDATOR_ID,
    success_message,
)
from omnibase_core.nodes.node_release_identity_gather_effect.handler import (
    NodeReleaseIdentityGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)


def main(argv: list[str] | None = None) -> int:
    """Run the legacy selectors, then write and render the canonical report."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=None,
        help="Git ref to diff against (e.g. origin/dev) to detect src/ changes.",
    )
    parser.add_argument(
        "--changed-file",
        dest="changed_files",
        action="append",
        default=[],
        help="Explicit changed file (repeatable). Overrides --base diffing.",
    )
    parser.add_argument(
        "filenames",
        nargs="*",
        help="Explicit changed paths, equivalent to --changed-file.",
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[4]),
        help="Repository root containing pyproject.toml.",
    )
    parser.add_argument(
        "--report-json",
        default=None,
        help="Write the canonical ValidationReport on PASS, FAIL and ERROR.",
    )
    args = parser.parse_args(argv)
    explicit = [*args.changed_files, *args.filenames]
    if explicit == ["-"]:
        explicit = [
            line.strip() for line in sys.stdin.read().splitlines() if line.strip()
        ]
    facts = NodeReleaseIdentityGatherEffect().handle(
        ModelReleaseIdentityGatherInput(
            repo_root=args.root,
            base=args.base,
            explicit_paths=tuple(explicit),
        )
    )
    code: int
    if facts.runtime_errors:
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, facts.runtime_errors
        )
        code = facts.runtime_exit_code
    else:
        report = NodeReleaseIdentityCheckCompute().handle(facts)
        code = (
            0
            if report.overall_status == "PASS"
            else 2
            if report.overall_status == "ERROR"
            else 1
        )
    if args.report_json is not None:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=args.report_json, report=report)
        )
    if report.overall_status == "PASS":
        sys.stdout.write(success_message(facts) + "\n")
    else:
        for finding in report.findings:
            sys.stderr.write(finding.message + "\n")
            if finding.remediation is not None:
                sys.stderr.write(finding.remediation + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
