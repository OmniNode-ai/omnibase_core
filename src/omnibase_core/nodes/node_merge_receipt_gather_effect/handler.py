# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""EFFECT handler that reads the PR watcher state, the ledger and the clones (OMN-21926)."""

import json
import subprocess
from pathlib import Path

from omnibase_core.models.merge_receipt.model_merge_receipt_gather_input import (
    ModelMergeReceiptGatherInput,
)
from omnibase_core.models.merge_receipt.model_merge_receipt_gather_output import (
    ModelMergeReceiptGatherOutput,
)
from omnibase_core.nodes.node_merge_receipt_gather_effect.facts_merge_receipt import (
    slot_seconds,
    watcher_facts,
)


def _changed_paths(clone: Path, base: str, head_sha: str) -> tuple[str, ...] | None:
    """Paths the head changes against its base in a canonical clone, or None if unreadable."""
    done = subprocess.run(
        ["git", "-C", str(clone), "diff", "--name-only", f"origin/{base}...{head_sha}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        return None
    return tuple(line for line in done.stdout.splitlines() if line)


class NodeMergeReceiptGatherEffect:
    """The I/O boundary: read files and git, hand typed facts to the pure checker."""

    def handle(
        self, request: ModelMergeReceiptGatherInput
    ) -> ModelMergeReceiptGatherOutput:
        """Read the state, the clones and the ledger once."""
        state = json.loads(request.state_path.read_text(encoding="utf-8"))
        facts, unreadable = watcher_facts(
            state,
            request.repos,
            request.check_names,
            lambda repo, _number, base, head: _changed_paths(
                request.clone_root / repo, base, head
            ),
        )
        rows: list[str] = []
        for path in request.ledger_paths:
            rows.extend(path.read_text(encoding="utf-8").splitlines())
        return ModelMergeReceiptGatherOutput(
            pull_requests=facts,
            unreadable=unreadable,
            slot_seconds=tuple(slot_seconds(rows, request.surface_pattern)),
        )
