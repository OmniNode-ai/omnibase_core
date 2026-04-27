# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ValidatorRuntimeProfiles (OMN-9886, plan Task 4).

Plan source: docs/plans/2026-04-26-runtime-lifecycle-hardening-plan.md (Task 4).

A node contract is "command-consuming" if its event_bus block subscribes to
at least one topic matching ``onex.cmd.*``. The validator fails when such a
contract has empty/absent ``runtime_profiles`` and the node id is not in the
explicit allowlist.

Both contract shapes are accepted for ``runtime_profiles`` (mirrors the
canonical extractor in
``omnibase_infra/runtime/auto_wiring/discovery.py::_extract_runtime_profiles``):
top-level ``runtime_profiles`` and ``descriptor.runtime_profiles``.

Both subscription shapes are accepted (Task 6 hardens the parser, but the
validator must not under-detect command consumers): classic
``event_bus.subscribe_topics: [str, ...]`` and nested
``event_bus.subscribe: [{topic: str, ...}, ...]``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from omnibase_core.enums import EnumSeverity
from omnibase_core.models.contracts.subcontracts.model_validator_rule import (
    ModelValidatorRule,
)
from omnibase_core.models.contracts.subcontracts.model_validator_subcontract import (
    ModelValidatorSubcontract,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.validation.validator_runtime_profiles import (
    ALLOWLIST_REASON_REQUIRED,
    RULE_RUNTIME_PROFILES_MISSING,
    ValidatorRuntimeProfiles,
    load_default_allowlist,
)


def _contract() -> ModelValidatorSubcontract:
    return ModelValidatorSubcontract(
        version=ModelSemVer(major=1, minor=0, patch=0),
        validator_id="runtime_profiles",
        validator_name="Runtime Profiles",
        validator_description="Enforce descriptor.runtime_profiles on command-consuming contracts.",
        target_patterns=["**/contract.yaml"],
        exclude_patterns=[],
        suppression_comments=[],
        fail_on_error=True,
        fail_on_warning=False,
        max_violations=0,
        severity_default=EnumSeverity.ERROR,
        rules=[
            ModelValidatorRule(
                rule_id=RULE_RUNTIME_PROFILES_MISSING,
                description="Reject command-consuming contracts without runtime_profiles.",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
        ],
    )


def _write(tmp_path: Path, payload: dict[str, object]) -> Path:
    p = tmp_path / "contract.yaml"
    p.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return p


@pytest.mark.unit
class TestValidatorRuntimeProfilesViolations:
    """Command-consuming contracts must declare runtime_profiles."""

    def test_classic_subscribe_topics_command_without_runtime_profiles_fails(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_orchestrator",
                "node_type": "orchestrator",
                "event_bus": {
                    "subscribe_topics": [
                        "onex.cmd.demo.start.v1",
                    ],
                },
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())

        issues = validator._validate_file(path, _contract())

        assert len(issues) == 1
        issue = issues[0]
        assert issue.code == RULE_RUNTIME_PROFILES_MISSING
        assert issue.severity == EnumSeverity.ERROR
        assert "runtime_profiles missing" in issue.message
        assert issue.file_path == path

    def test_nested_subscribe_command_without_runtime_profiles_fails(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_consumer",
                "node_type": "compute",
                "event_bus": {
                    "subscribe": [
                        {"topic": "onex.cmd.demo.do.v1", "consumer_group": "g1"},
                    ],
                },
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())

        issues = validator._validate_file(path, _contract())

        assert len(issues) == 1
        assert "runtime_profiles missing" in issues[0].message

    def test_descriptor_block_without_runtime_profiles_still_fails(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_orchestrator",
                "node_type": "orchestrator",
                "descriptor": {
                    "purity": "effectful",
                    # runtime_profiles intentionally absent
                },
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.start.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert len(issues) == 1
        assert "runtime_profiles missing" in issues[0].message

    def test_empty_runtime_profiles_list_treated_as_missing(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_orchestrator",
                "node_type": "orchestrator",
                "runtime_profiles": [],
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.start.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert len(issues) == 1


@pytest.mark.unit
class TestValidatorRuntimeProfilesPasses:
    """Compliant contracts and allowlisted read-only nodes must pass."""

    def test_top_level_runtime_profiles_satisfies_validator(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_orchestrator",
                "node_type": "orchestrator",
                "runtime_profiles": ["effects"],
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.start.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert issues == ()

    def test_descriptor_runtime_profiles_satisfies_validator(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_build_loop_orchestrator",
                "node_type": "orchestrator",
                "descriptor": {
                    "purity": "effectful",
                    "runtime_profiles": ["effects"],
                },
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.start.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert issues == ()

    def test_event_only_contract_with_no_command_subscription_passes(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_projection",
                "node_type": "compute",
                "event_bus": {
                    "subscribe_topics": ["onex.evt.demo.completed.v1"],
                },
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert issues == ()

    def test_no_event_bus_block_passes(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_compute",
                "node_type": "compute",
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert issues == ()

    def test_allowlisted_read_only_node_passes(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_readonly_demo",
                "node_type": "compute",
                "event_bus": {"subscribe_topics": ["onex.cmd.readonly.probe.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(
            contract=_contract(), allowlist={"node_readonly_demo"}
        )
        issues = validator._validate_file(path, _contract())
        assert issues == ()


@pytest.mark.unit
class TestValidatorRuntimeProfilesAllowlistFile:
    """The default allowlist YAML must require an explicit reason per entry."""

    def test_default_allowlist_loads_with_reason_per_entry(self) -> None:
        entries = load_default_allowlist()
        for node_id, reason in entries.items():
            assert isinstance(node_id, str) and node_id, (
                "node_id must be non-empty string"
            )
            assert isinstance(reason, str) and reason.strip(), (
                f"allowlist entry {node_id!r} missing a non-empty 'reason' "
                f"({ALLOWLIST_REASON_REQUIRED})"
            )
