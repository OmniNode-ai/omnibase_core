# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ValidatorDemoPathTopicCoherence -- demo-path topic coherence gate (OMN-12777).

Scoped to the demo-path contracts only (``metadata.demo_path: true``).

Asserts (fail on any):
  (a) RULE_HAND_AUTHORED_LITERAL  -- no hand-authored topic string literals in
      Python source files under the demo-path node directories; generated
      artifacts are allowed only if derived from the contract registry.
  (b) RULE_PUBLISH_SUBSCRIBE_MISMATCH -- every demo-path ``publish_topics`` entry
      byte-matches some consumer ``subscribe_topics`` entry (no prefix drift).
  (c) RULE_ORPHAN_PRODUCER -- no producer topic on the demo path with zero
      subscribers anywhere else on the demo path.
  (d) RULE_ORPHAN_CONSUMER -- no consumer topic on the demo path with zero
      producers anywhere else on the demo path.
  (e) RULE_WIDGET_TOPIC_NO_PRODUCER -- every demo-visible widget topic declared
      in ``metadata.widget_topics`` has at least one producing node on the demo
      path (i.e., it appears in some ``publish_topics``).

Usage:
    # As a standalone script / pre-commit entry point:
    python -m omnibase_core.validation.validator_demo_path_topic_coherence \\
        /path/to/omnibase_infra /path/to/omnimarket /path/to/omnidash

    # Programmatic:
    from pathlib import Path
    from omnibase_core.validation.validator_demo_path_topic_coherence import (
        ValidatorDemoPathTopicCoherence,
    )
    validator = ValidatorDemoPathTopicCoherence(
        repo_roots=[Path("omnibase_infra"), Path("omnimarket")]
    )
    result = validator.run()
    if not result.is_valid:
        for issue in result.issues:
            print(issue.message)

Suppression:
    Lines carrying ``# onex-demo-gate-allow: <reason>`` are excluded from the
    hand-authored-literal scan.  Contract files (``contract.yaml``) are always
    excluded from the literal scan (they are the source of truth).

Related: OMN-12777, Wave 0A of the bus-native SEA + delegation + dashboard
demo plan (``docs/plans/2026-06-07-bus-native-sea-demo-full-plan.md``).
"""

from __future__ import annotations

import re
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from omnibase_core.enums.enum_severity import EnumSeverity
from omnibase_core.models.common.model_validation_issue import ModelValidationIssue
from omnibase_core.models.common.model_validation_metadata import (
    ModelValidationMetadata,
)
from omnibase_core.models.common.model_validation_result import ModelValidationResult
from omnibase_core.models.primitives.model_semver import ModelSemVer

# ---------------------------------------------------------------------------
# Rule identifiers (exported so tests can reference them symbolically)
# ---------------------------------------------------------------------------

RULE_HAND_AUTHORED_LITERAL: str = "demo_path_hand_authored_literal"
RULE_PUBLISH_SUBSCRIBE_MISMATCH: str = "demo_path_publish_subscribe_mismatch"
RULE_ORPHAN_PRODUCER: str = "demo_path_orphan_producer"
RULE_ORPHAN_CONSUMER: str = "demo_path_orphan_consumer"
RULE_WIDGET_TOPIC_NO_PRODUCER: str = "demo_path_widget_topic_no_producer"

# ---------------------------------------------------------------------------
# Suppression marker for the hand-authored-literal scan
# ---------------------------------------------------------------------------

_LITERAL_SUPPRESSION_MARKER: str = "onex-demo-gate-allow:"

# Pattern for bare onex topic string literals in Python/TypeScript source
_ONEX_TOPIC_LITERAL: re.Pattern[str] = re.compile(
    r"""["']onex\.(cmd|evt|dlq|snapshot|intent)\.[^"'\s]+["']"""
)

# ---------------------------------------------------------------------------
# Demo-path contract data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DemoPathContract:
    """Parsed representation of a single demo-path contract.yaml."""

    name: str  # node directory name (from contract file parent dir)
    contract_path: Path
    subscribe_topics: frozenset[str]
    publish_topics: frozenset[str]
    widget_topics: frozenset[str]  # metadata.widget_topics


# ---------------------------------------------------------------------------
# Contract loader
# ---------------------------------------------------------------------------


def load_demo_path_contracts(repo_roots: list[Path]) -> list[DemoPathContract]:
    """Scan ``repo_roots`` for contract.yaml files with ``metadata.demo_path: true``.

    Walks each root recursively, reads every ``contract.yaml``, and returns
    ``DemoPathContract`` instances for those with the demo_path marker set.

    Args:
        repo_roots: Directories to scan.  Each root is walked recursively.

    Returns:
        List of parsed demo-path contracts (may be empty).
    """
    contracts: list[DemoPathContract] = []

    for root in repo_roots:
        if not root.is_dir():
            continue
        for contract_path in sorted(root.rglob("contract.yaml")):
            # Skip virtual-env or build artifacts
            parts = contract_path.parts
            if any(
                p in parts
                for p in (
                    ".venv",
                    "__pycache__",
                    "node_modules",
                    ".git",
                    "build",
                    "dist",
                )
            ):
                continue

            try:
                raw = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001  # boundary-ok: skip unreadable/invalid contracts
                continue

            if not isinstance(raw, dict):
                continue

            metadata: Any = raw.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            if not metadata.get("demo_path", False):
                continue

            event_bus: Any = raw.get("event_bus", {})
            if not isinstance(event_bus, dict):
                event_bus = {}

            subscribe_raw: Any = event_bus.get("subscribe_topics") or []
            publish_raw: Any = event_bus.get("publish_topics") or []
            widget_raw: Any = metadata.get("widget_topics") or []

            contracts.append(
                DemoPathContract(
                    name=contract_path.parent.name,
                    contract_path=contract_path,
                    subscribe_topics=frozenset(str(t) for t in subscribe_raw),
                    publish_topics=frozenset(str(t) for t in publish_raw),
                    widget_topics=frozenset(str(t) for t in widget_raw),
                )
            )

    return contracts


# ---------------------------------------------------------------------------
# Topic registry and coherence checks
# ---------------------------------------------------------------------------


@dataclass
class DemoPathTopicRegistry:
    """Aggregated topic view across all demo-path contracts."""

    # Map topic -> set of node names that publish it
    producers: dict[str, set[str]] = field(default_factory=dict)
    # Map topic -> set of node names that subscribe to it
    consumers: dict[str, set[str]] = field(default_factory=dict)
    # All widget topics declared across contracts
    widget_topics: set[str] = field(default_factory=set)

    @classmethod
    def from_contracts(cls, contracts: list[DemoPathContract]) -> DemoPathTopicRegistry:
        registry = cls()
        for contract in contracts:
            for topic in contract.publish_topics:
                registry.producers.setdefault(topic, set()).add(contract.name)
            for topic in contract.subscribe_topics:
                registry.consumers.setdefault(topic, set()).add(contract.name)
            registry.widget_topics.update(contract.widget_topics)
        return registry

    def find_publish_subscribe_mismatches(self) -> list[str]:
        """Return descriptions of topics that are published but have no subscriber.

        A mismatch means some node's ``publish_topics`` entry byte-mismatches
        every ``subscribe_topics`` entry across all demo-path contracts.
        """
        mismatches: list[str] = []
        for topic, publishers in sorted(self.producers.items()):
            if topic not in self.consumers:
                mismatches.append(
                    f"topic {topic!r} published by {sorted(publishers)} "
                    "but no demo-path consumer subscribes to it (byte mismatch or orphan)"
                )
        return mismatches

    def find_orphan_producers(self) -> list[str]:
        """Return descriptions of topics that are published but never consumed.

        Note: this is the same check as ``find_publish_subscribe_mismatches``
        but expressed as orphan producers for rule-code clarity.
        """
        orphans: list[str] = []
        for topic, publishers in sorted(self.producers.items()):
            if topic not in self.consumers:
                orphans.append(
                    f"orphan producer: topic {topic!r} published by "
                    f"{sorted(publishers)} but has no demo-path subscriber"
                )
        return orphans

    def find_orphan_consumers(self) -> list[str]:
        """Return descriptions of topics that are subscribed to but never produced."""
        orphans: list[str] = []
        for topic, subscribers in sorted(self.consumers.items()):
            if topic not in self.producers:
                orphans.append(
                    f"orphan consumer: topic {topic!r} subscribed by "
                    f"{sorted(subscribers)} but has no demo-path producer"
                )
        return orphans

    def find_widget_topics_without_producers(self) -> list[str]:
        """Return descriptions of widget topics that have no producing node."""
        missing: list[str] = []
        for topic in sorted(self.widget_topics):
            if topic not in self.producers:
                missing.append(
                    f"widget topic {topic!r} has no producing node on the demo path"
                )
        return missing


# ---------------------------------------------------------------------------
# Hand-authored literal scanner
# ---------------------------------------------------------------------------


def _scan_for_literals(
    contract_path: Path,
) -> list[tuple[Path, int, str]]:
    """Scan Python source files in the node directory for bare topic literals.

    Only files adjacent to the contract (i.e., in ``contract_path.parent/**``)
    are scanned. ``contract.yaml`` itself is always skipped (it is the source
    of truth). Lines containing the suppression marker are also skipped.

    Returns:
        List of (file_path, line_number, matched_literal) tuples.
    """
    node_dir = contract_path.parent
    findings: list[tuple[Path, int, str]] = []

    for py_file in sorted(node_dir.rglob("*.py")):
        # Skip virtual-env / build artifacts
        parts = py_file.parts
        if any(
            p in parts
            for p in (".venv", "__pycache__", "node_modules", ".git", "build", "dist")
        ):
            continue

        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for lineno, line in enumerate(text.splitlines(), start=1):
            if _LITERAL_SUPPRESSION_MARKER in line:
                continue
            # Also honor the canonical hardcoded-topics suppression markers
            if "onex-topic-sot" in line or "onex-topic-allow:" in line:
                continue
            for match in _ONEX_TOPIC_LITERAL.finditer(line):
                findings.append((py_file, lineno, match.group()))

    return findings


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------


class ValidatorDemoPathTopicCoherence:
    """Demo-path topic coherence gate.

    Runs all four coherence assertions over the set of contracts that carry
    ``metadata.demo_path: true`` within the specified repo roots.

    Attributes:
        repo_roots: Directories to scan for demo-path contracts.
    """

    validator_id: str = "demo_path_topic_coherence"

    def __init__(self, repo_roots: list[Path]) -> None:
        self.repo_roots = repo_roots

    def run(self) -> ModelValidationResult[None]:
        """Execute all coherence checks and return an aggregated result."""
        start = time.time()
        issues: list[ModelValidationIssue] = []

        contracts = load_demo_path_contracts(self.repo_roots)

        if contracts:
            registry = DemoPathTopicRegistry.from_contracts(contracts)

            # (b) publish/subscribe byte-match
            for desc in registry.find_publish_subscribe_mismatches():
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.ERROR,
                        message=desc,
                        code=RULE_PUBLISH_SUBSCRIBE_MISMATCH,
                        rule_name=RULE_PUBLISH_SUBSCRIBE_MISMATCH,
                    )
                )

            # (c) orphan producers
            for desc in registry.find_orphan_producers():
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.ERROR,
                        message=desc,
                        code=RULE_ORPHAN_PRODUCER,
                        rule_name=RULE_ORPHAN_PRODUCER,
                    )
                )

            # (d) orphan consumers
            for desc in registry.find_orphan_consumers():
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.ERROR,
                        message=desc,
                        code=RULE_ORPHAN_CONSUMER,
                        rule_name=RULE_ORPHAN_CONSUMER,
                    )
                )

            # (e) widget topics without producers
            for desc in registry.find_widget_topics_without_producers():
                issues.append(
                    ModelValidationIssue(
                        severity=EnumSeverity.ERROR,
                        message=desc,
                        code=RULE_WIDGET_TOPIC_NO_PRODUCER,
                        rule_name=RULE_WIDGET_TOPIC_NO_PRODUCER,
                    )
                )

            # (a) hand-authored literals in source files adjacent to demo-path nodes
            for contract in contracts:
                for file_path, lineno, literal in _scan_for_literals(
                    contract.contract_path
                ):
                    issues.append(
                        ModelValidationIssue(
                            severity=EnumSeverity.ERROR,
                            message=(
                                f"hand-authored topic literal {literal!r} "
                                f"in demo-path source file -- use a constant from the "
                                f"contract registry (OMN-12777)"
                            ),
                            code=RULE_HAND_AUTHORED_LITERAL,
                            rule_name=RULE_HAND_AUTHORED_LITERAL,
                            file_path=file_path,
                            line_number=lineno,
                        )
                    )

        duration_ms = int((time.time() - start) * 1000)
        has_errors = any(i.severity == EnumSeverity.ERROR for i in issues)
        is_valid = not has_errors

        if issues:
            summary = (
                f"Demo-path topic coherence: FAILED — {len(issues)} issue(s) found"
            )
        else:
            summary = (
                f"Demo-path topic coherence: OK — {len(contracts)} contract(s) checked"
            )

        metadata = ModelValidationMetadata.model_validate(
            {
                "validation_type": self.validator_id,
                "duration_ms": duration_ms,
                "files_processed": len(contracts),
                "rules_applied": 5,
                "timestamp": datetime.now(tz=UTC).isoformat(),
                "validator_version": ModelSemVer(major=1, minor=0, patch=0),
                "violations_found": len(issues),
                "files_with_violations": sorted(
                    {str(i.file_path) for i in issues if i.file_path}
                ),
                "files_with_violations_count": len(
                    {str(i.file_path) for i in issues if i.file_path}
                ),
                "strict_mode": True,
            }
        )

        return ModelValidationResult[None](
            is_valid=is_valid,
            issues=sorted(
                issues,
                key=lambda i: (
                    str(i.file_path or ""),
                    i.line_number or 0,
                    i.code or "",
                ),
            ),
            summary=summary,
            metadata=metadata,
        )

    @staticmethod
    def get_exit_code(result: ModelValidationResult[None]) -> int:
        """Map result to CLI exit code (0 = pass, 1 = fail)."""
        return 0 if result.is_valid else 1


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point.

    Usage:
        onex-demo-path-topic-gate <repo_root> [<repo_root> ...]
        python -m omnibase_core.validation.validator_demo_path_topic_coherence <roots...>
    """
    args = sys.argv[1:]
    if not args:
        print(
            "Usage: onex-demo-path-topic-gate <repo_root> [<repo_root> ...]",
            file=sys.stderr,
        )
        sys.exit(2)

    repo_roots = [Path(a).resolve() for a in args]
    missing = [str(r) for r in repo_roots if not r.is_dir()]
    if missing:
        print(f"Error: directories not found: {missing}", file=sys.stderr)
        sys.exit(2)

    validator = ValidatorDemoPathTopicCoherence(repo_roots=repo_roots)
    result = validator.run()

    print(result.summary)
    if result.issues:
        print()
        for issue in result.issues:
            location = ""
            if issue.file_path:
                location = str(issue.file_path)
                if issue.line_number:
                    location += f":{issue.line_number}"
                location += ": "
            print(f"  [ERROR] {location}{issue.message}")

    sys.exit(validator.get_exit_code(result))


if __name__ == "__main__":
    main()
