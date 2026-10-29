# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pure node-home rule of the canonical-file-shape check: new nodes belong in omnimarket (OMN-20702, OMN-21515).

A new node directory whose ``contract.yaml`` lists a validator category under the
contract field named by the rule row is admitted; every name, pattern, category
and message comes from the ``node-home:*`` rows of the validator contract.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath

from omnibase_core.models.validation.model_canonical_file_shape_rule_set import (
    ModelCanonicalFileShapeRuleSet,
)
from omnibase_core.models.validation.model_canonical_file_shape_rules import (
    ModelCanonicalFileShapeRules,
)
from omnibase_core.models.validation.model_canonical_file_shape_text import (
    ModelCanonicalFileShapeText,
)
from omnibase_core.models.validation.model_node_home_ratchet_finding import (
    ModelNodeHomeRatchetFinding,
    NodeHomeFindingCode,
)
from omnibase_core.models.validation.model_node_home_ratchet_request import (
    ModelNodeHomeRatchetRequest,
)
from omnibase_core.models.validation.model_node_home_ratchet_result import (
    ModelNodeHomeRatchetResult,
)
from omnibase_core.validation.checker_canonical_file_shape import (
    contract_tags,
    parse_baseline,
)

CODE_OUTSIDE_MARKET: NodeHomeFindingCode = "node-outside-market"
CODE_BASELINE_STALE: NodeHomeFindingCode = "baseline-stale"
CODE_BASELINE_GROWTH: NodeHomeFindingCode = "baseline-growth"
CODE_BASELINE_REMOVED: NodeHomeFindingCode = "baseline-removed"
CODE_ENTRY_POINT: NodeHomeFindingCode = "entry-point-outside-market"
RULE_PREFIX = "node-home:"


def eligible(path: PurePosixPath, p: ModelCanonicalFileShapeRules) -> bool:
    """A path outside the ignored components and every hidden directory."""
    return not (set(p.node_home_ignored_components) & set(path.parts)) and not any(
        component.startswith(p.node_home_hidden_prefix) for component in path.parts
    )


def node_directories(
    tracked_paths: Iterable[str],
    node_class_paths: Iterable[str],
    p: ModelCanonicalFileShapeRules,
) -> tuple[str, ...]:
    """Directories holding a node: a contract with a handler, or a ``Node*`` class."""
    files = {
        posix_path
        for path in tracked_paths
        if eligible(posix_path := PurePosixPath(path), p)
    }
    contracts = {path.parent for path in files if path.name == p.contract_file_name}
    direct_handlers = {
        path.parent
        for path in files
        if path.suffix == p.node_home_source_suffix
        and (
            path.name.startswith(p.node_home_handler_prefix)
            or path.name == p.node_home_node_file
        )
    }
    handler_subdirs = {
        parent.parent
        for path in files
        if path.suffix == p.node_home_source_suffix
        for parent in path.parents
        if parent.name == p.node_home_handlers_dir
    }
    nodes = {
        directory
        for directory in contracts
        if directory in direct_handlers
        or directory in handler_subdirs
        or p.node_home_nodes_dir in directory.parts
    }
    nodes.update(
        path.parent
        for text_path in node_class_paths
        if (path := PurePosixPath(text_path)) in files
        and path.suffix == p.node_home_source_suffix
        and (
            path.parent.name.startswith(p.node_home_node_dir_prefix)
            or path.parent in contracts
        )
    )
    nodes = {directory for directory in nodes if eligible(directory, p)}
    return tuple(sorted(directory.as_posix() for directory in nodes))


def _declares_admitted_category(
    contract_text: str | None, p: ModelCanonicalFileShapeRules
) -> bool:
    return bool(
        set(p.node_home_admitted_categories)
        & contract_tags(contract_text, p.node_home_admitted_field)
    )


def _admitted_directories(
    nodes: set[str],
    contract_texts: Iterable[ModelCanonicalFileShapeText],
    p: ModelCanonicalFileShapeRules,
) -> set[str]:
    texts = {entry.path: entry.text for entry in contract_texts}
    return {
        directory
        for directory in nodes
        if _declares_admitted_category(
            texts.get(f"{directory}/{p.contract_file_name}"), p
        )
    }


def _toml_key_path(parts: Iterable[str]) -> str:
    return ".".join(f'"{part}"' if "." in part else part for part in parts)


def _entries(text: str | None) -> set[str]:
    return set(parse_baseline(text))


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

    def __init__(self, rules: ModelCanonicalFileShapeRuleSet) -> None:
        self._rules = rules

    def _finding(
        self, code: NodeHomeFindingCode, path: str, message: str
    ) -> list[ModelNodeHomeRatchetFinding]:
        if f"{RULE_PREFIX}{code}" not in self._rules.enabled:
            return []
        return [ModelNodeHomeRatchetFinding(code=code, path=path, message=message)]

    def check(self, request: ModelNodeHomeRatchetRequest) -> ModelNodeHomeRatchetResult:
        """Check node placement and baseline shrinking using only the supplied inputs."""
        p = self._rules.parameters
        directories = node_directories(
            request.tracked_paths, request.node_class_paths, p
        )
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
        admitted = _admitted_directories(nodes, request.node_contract_texts, p)
        for path in sorted(nodes - baseline - set(inherited) - admitted):
            findings += self._finding(
                CODE_OUTSIDE_MARKET, path, p.node_home_outside_market_text
            )
        for path in sorted(baseline - nodes - renamed_from):
            findings += self._finding(
                CODE_BASELINE_STALE,
                p.node_home_baseline_path,
                p.node_home_baseline_stale_text.format(path=path),
            )
        for path in sorted(baseline - allowed_baseline - set(inherited)):
            findings += self._finding(
                CODE_BASELINE_GROWTH,
                p.node_home_baseline_path,
                p.node_home_baseline_growth_text.format(path=path),
            )
        if (
            request.base_baseline_text is not None
            and request.head_baseline_text is None
        ):
            findings += self._finding(
                CODE_BASELINE_REMOVED,
                p.node_home_baseline_path,
                p.node_home_baseline_removed_text,
            )
        for name in sorted(request.head_entry_points - request.base_entry_points):
            findings += self._finding(
                CODE_ENTRY_POINT,
                f"pyproject.toml:{_toml_key_path(p.node_home_entry_point_path)}.{name}",
                p.node_home_entry_point_text,
            )
        return ModelNodeHomeRatchetResult(
            node_directories=directories, findings=tuple(findings)
        )
