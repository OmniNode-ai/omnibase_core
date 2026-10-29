# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure node-home rule of the canonical-file-shape check: new nodes belong in omnimarket (OMN-20702, OMN-21515)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath

from omnibase_core.models.validation.model_node_home_ratchet_finding import (
    ModelNodeHomeRatchetFinding,
)
from omnibase_core.models.validation.model_node_home_ratchet_request import (
    ModelNodeHomeRatchetRequest,
)
from omnibase_core.models.validation.model_node_home_ratchet_result import (
    ModelNodeHomeRatchetResult,
)

NODE_HOME_BASELINE = ".onex_ratchets/node_home_baseline.txt"
_IGNORED_COMPONENTS = frozenset(
    {"tests", "test", "fixtures", "examples", "__pycache__", "docs"}
)


def _eligible(path: PurePosixPath) -> bool:
    return not (_IGNORED_COMPONENTS & set(path.parts)) and not any(
        component.startswith(".") for component in path.parts
    )


def _node_directories(
    tracked_paths: Iterable[str], node_class_paths: Iterable[str]
) -> tuple[str, ...]:
    files = {
        posix_path
        for path in tracked_paths
        if _eligible(posix_path := PurePosixPath(path))
    }
    contracts = {path.parent for path in files if path.name == "contract.yaml"}
    direct_handlers = {
        path.parent
        for path in files
        if path.suffix == ".py"
        and (path.name.startswith("handler") or path.name == "node.py")
    }
    handler_subdirs = {
        parent.parent
        for path in files
        if path.suffix == ".py"
        for parent in path.parents
        if parent.name == "handlers"
    }
    nodes = {
        directory
        for directory in contracts
        if directory in direct_handlers
        or directory in handler_subdirs
        or "nodes" in directory.parts
    }
    nodes.update(
        path.parent
        for text_path in node_class_paths
        if (path := PurePosixPath(text_path)) in files
        and path.suffix == ".py"
        and (path.parent.name.startswith("node_") or path.parent in contracts)
    )
    nodes = {directory for directory in nodes if _eligible(directory)}
    return tuple(sorted(directory.as_posix() for directory in nodes))


def _entries(text: str | None) -> set[str]:
    return {
        line.strip()
        for line in (text or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def _inherited_directories(
    request: ModelNodeHomeRatchetRequest,
    nodes: set[str],
    base_entries: set[str],
) -> dict[str, str]:
    """``new node directory -> baselined old directory`` for a git-detected rename.

    A node directory renamed within the repository keeps its place in the
    shrink-only baseline, as a renamed baselined file does; the directory it
    replaces must be gone.
    """
    inherited: dict[str, str] = {}
    for old_path, new_path in request.renamed_paths:
        old_dirs = [entry for entry in base_entries if old_path.startswith(f"{entry}/")]
        new_dirs = [node for node in nodes if new_path.startswith(f"{node}/")]
        for old_dir in old_dirs:
            for new_dir in new_dirs:
                if new_dir != old_dir and old_dir not in nodes:
                    inherited[new_dir] = old_dir
    return inherited


class NodeHomeRule:
    """Check supplied node snapshots without filesystem or Git dependencies."""

    def check(self, request: ModelNodeHomeRatchetRequest) -> ModelNodeHomeRatchetResult:
        """Check node placement and baseline shrinking using only the supplied inputs."""
        directories = _node_directories(request.tracked_paths, request.node_class_paths)
        findings: list[ModelNodeHomeRatchetFinding] = []
        nodes = set(directories)
        baseline = _entries(request.head_baseline_text)
        allowed_baseline = (
            _entries(request.base_baseline_text)
            if request.base_baseline_text is not None
            else request.base_node_directories
        )
        inherited = _inherited_directories(request, nodes, set(allowed_baseline))
        renamed_from = set(inherited.values())
        for path in sorted(nodes - baseline - set(inherited)):
            findings.append(
                ModelNodeHomeRatchetFinding(
                    code="node-outside-market",
                    path=path,
                    message="new or renamed node directory; the node moves to omnimarket instead",
                )
            )
        for path in sorted(baseline - nodes - renamed_from):
            findings.append(
                ModelNodeHomeRatchetFinding(
                    code="baseline-stale",
                    path=NODE_HOME_BASELINE,
                    message=f"entry '{path}' is no longer a node directory; delete the line; a renamed node moves to omnimarket instead",
                )
            )
        for path in sorted(baseline - allowed_baseline - set(inherited)):
            findings.append(
                ModelNodeHomeRatchetFinding(
                    code="baseline-growth",
                    path=NODE_HOME_BASELINE,
                    message=f"entry '{path}' is new; the baseline only shrinks and bootstraps from base-revision nodes; the node moves to omnimarket instead",
                )
            )
        if (
            request.base_baseline_text is not None
            and request.head_baseline_text is None
        ):
            findings.append(
                ModelNodeHomeRatchetFinding(
                    code="baseline-removed",
                    path=NODE_HOME_BASELINE,
                    message="the baseline file must remain, even when empty; it can only shrink",
                )
            )
        for name in sorted(request.head_entry_points - request.base_entry_points):
            findings.append(
                ModelNodeHomeRatchetFinding(
                    code="entry-point-outside-market",
                    path=f'pyproject.toml:project.entry-points."onex.nodes".{name}',
                    message="a new onex.nodes registration outside omnimarket; register the node in omnimarket instead",
                )
            )
        return ModelNodeHomeRatchetResult(
            node_directories=directories, findings=tuple(findings)
        )
