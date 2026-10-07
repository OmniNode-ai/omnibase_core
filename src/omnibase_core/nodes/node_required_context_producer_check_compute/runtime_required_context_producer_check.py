# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Gather repository sources, validate required producers, and render a report."""

import argparse
import sys
from pathlib import Path

from omnibase_core.models.nodes.required_context_producer_check.model_required_context_producer_gather_input import (
    ModelRequiredContextProducerGatherInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_required_context_producer_check_compute.handler import (
    NodeRequiredContextProducerCheckCompute,
)
from omnibase_core.nodes.node_required_context_producer_check_compute.required_context_producer_rules import (
    VALIDATOR_ID,
    manifest_rows,
)
from omnibase_core.nodes.node_required_context_producer_gather_effect.handler import (
    NodeRequiredContextProducerGatherEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)


def main(argv: list[str] | None = None) -> int:
    """Run the paired nodes and write reports on PASS, FAIL, and ERROR."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[4]))
    parser.add_argument("--base", default=None, help="Base Git ref, e.g. origin/dev.")
    parser.add_argument("--report-json", default=None)
    args = parser.parse_args(argv)
    facts = NodeRequiredContextProducerGatherEffect().handle(
        ModelRequiredContextProducerGatherInput(repo_root=args.root, base=args.base)
    )
    if facts.runtime_errors:
        report = ModelValidationReport.from_runtime_errors(
            VALIDATOR_ID, facts.runtime_errors
        )
        code: int = facts.runtime_exit_code
    else:
        report = NodeRequiredContextProducerCheckCompute().handle(facts)
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
        count = sum(
            row["mode"] == "REQUIRED" for row in manifest_rows(facts.head_manifest_text)
        )
        sys.stdout.write(
            f"OK: checked {count} REQUIRED rows; all required contexts retain producers.\n"
        )
    else:
        for finding in report.findings:
            sys.stderr.write(finding.message + "\n")
            if finding.remediation is not None:
                sys.stderr.write(finding.remediation + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
