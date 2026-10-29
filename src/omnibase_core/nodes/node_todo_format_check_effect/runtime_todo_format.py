# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the todo-format hook (OMN-20068).

Usage::

    python -m omnibase_core.nodes.node_todo_format_check_effect.runtime_todo_format [files...]

Exit code 0 = clean. Exit code 1 = violations found.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from omnibase_core.models.validation.model_todo_format_request import (
    ModelTodoFormatRequest,
)
from omnibase_core.nodes.node_todo_format_check_effect.handler_todo_format import (
    TICKET_FORMAT,
    HandlerTodoFormat,
)

__all__ = ["main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the exported hook on the given files, or command-line arguments."""
    files = sys.argv[1:] if argv is None else argv
    all_violations = (
        HandlerTodoFormat().handle(ModelTodoFormatRequest(paths=tuple(files))).findings
    )
    if all_violations:
        for finding in all_violations:
            sys.stdout.write(f"{finding.format()}\n")
        sys.stdout.write(
            f"\n{len(all_violations)} violation(s). Use format: {TICKET_FORMAT}\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
