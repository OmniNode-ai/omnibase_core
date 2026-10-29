# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pre-commit and CI adapter for the canonical documentation EFFECT handler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.models.nodes.readme_only_docs.model_readme_only_docs_input import (
    ModelReadmeOnlyDocsInput,
)
from omnibase_core.models.nodes.validation_report_write.model_validation_report_write_input import (
    ModelValidationReportWriteInput,
)
from omnibase_core.nodes.node_git_file_listing_effect.handler_readme_only_docs import (
    HandlerReadmeOnlyDocs,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler import (
    NodeValidationReportWriteEffect,
)
from omnibase_core.nodes.node_validation_report_write_effect.handler_validator_run_events import (
    HandlerValidatorRunEvents,
)


def main(argv: list[str] | None = None) -> int:
    """Scan every indexed path and emit run/fire events on every verdict."""
    parser = argparse.ArgumentParser(
        description="Refuse tracked documentation except root README.md and declared machine inputs."
    )
    parser.add_argument("--root", type=Path, default=Path())
    parser.add_argument("--report-json")
    args = parser.parse_args(argv)
    report = HandlerReadmeOnlyDocs().handle(ModelReadmeOnlyDocsInput(root=args.root))
    if args.report_json:
        NodeValidationReportWriteEffect().handle(
            ModelValidationReportWriteInput(report_path=args.report_json, report=report)
        )
    for finding in report.findings:
        sys.stderr.write(f"{finding.location or 'repository'}: {finding.message}\n")
    for event in HandlerValidatorRunEvents().handle(report).events:
        sys.stdout.write(event.model_dump_json() + "\n")
    return (
        2 if report.overall_status == "ERROR" else int(report.overall_status != "PASS")
    )


if __name__ == "__main__":
    sys.exit(main())
