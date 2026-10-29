# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the no-hardcoded-topics hook (OMN-20074, OMN-21518).

Reads the named files through the source-file gather EFFECT, loads the rules from
the ``no_hardcoded_topics`` validator contract and hands both to the pure
``HandlerNoHardcodedTopics``. Usage::

    python -m omnibase_core.nodes.node_no_hardcoded_topics_check_compute.runtime_no_hardcoded_topics_check [files...]

Exit code 0 = clean. Exit code 1 = violations found, or a named file unreadable.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from omnibase_core.models.nodes.no_hardcoded_topics_check.model_no_hardcoded_topics_check_input import (
    ModelNoHardcodedTopicsCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.nodes.node_no_hardcoded_topics_check_compute.handler_no_hardcoded_topics import (
    HandlerNoHardcodedTopics,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)
from omnibase_core.validation.validator_no_hardcoded_topics import (
    ValidatorNoHardcodedTopics,
    load_rules,
)

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the exported hook on the given files, or command-line arguments."""
    paths = list(sys.argv[1:] if argv is None else argv)
    if not paths:
        return 0
    gathered = NodeSourceFileGatherEffect().handle(
        ModelSourceFileGatherInput(
            root=".",
            explicit_paths=paths,
            include_patterns=["**/*"],
            decode_errors="replace",
        )
    )
    if gathered.skipped:
        for skipped in gathered.skipped:
            sys.stdout.write(f"ERROR: {skipped.path}: {skipped.reason}\n")
        return 1
    rules = load_rules(ValidatorNoHardcodedTopics().contract)
    report = HandlerNoHardcodedTopics().handle(
        ModelNoHardcodedTopicsCheckInput(
            files=[
                ModelSourceFile(path=f.path, source=f.source) for f in gathered.files
            ],
            rules=rules,
        )
    )
    if report.findings:
        for finding in report.findings:
            sys.stdout.write(f"{finding.message}\n")
        sys.stdout.write(
            f"\n{len(report.findings)} violation(s). {rules.remediation}\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
