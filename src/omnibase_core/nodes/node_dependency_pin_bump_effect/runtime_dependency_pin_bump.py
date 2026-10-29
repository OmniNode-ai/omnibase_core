# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""CLI runtime of the dependency pin bump (OMN-21478).

The workflow refreshes the consumer's lockfile after this runtime succeeds.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.version_drift.model_dependency_pin_bump_request import (
    ModelDependencyPinBumpRequest,
)
from omnibase_core.nodes.node_dependency_pin_bump_effect.handler_dependency_pin_bump import (
    HandlerDependencyPinBump,
)

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """CLI entry: zero for a changed pin or no-op, nonzero for invalid input."""
    parser = argparse.ArgumentParser(
        description="Bump an opted-in consumer's omnibase-core dev tag."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--dependency-tag", required=True)
    args = parser.parse_args(argv)
    try:
        changed = (
            HandlerDependencyPinBump()
            .handle(
                ModelDependencyPinBumpRequest(
                    manifest=args.manifest,
                    repo=args.repo,
                    repo_root=args.repo_root,
                    dependency_tag=args.dependency_tag,
                )
            )
            .changed_path
        )
    except (OSError, ModelOnexError) as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1
    if changed is not None:
        sys.stdout.write(f"CHANGED: {changed} (tag -> {args.dependency_tag})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
