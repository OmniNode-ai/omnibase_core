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
    RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE,
    RULE_RUNTIME_PROFILE_UNREGISTERED,
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
            ModelValidatorRule(
                rule_id=RULE_RUNTIME_PROFILE_UNREGISTERED,
                description="Reject contracts naming an unregistered runtime profile.",
                severity=EnumSeverity.ERROR,
                enabled=True,
            ),
            ModelValidatorRule(
                rule_id=RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE,
                description="Reject subscribing reducer/effect naming no consumer lane.",
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


@pytest.mark.unit
class TestValidatorRuntimeProfileUnregistered:
    """OMN-12957: declared profiles must be members of the canonical registry."""

    def test_unregistered_profile_fails(self, tmp_path: Path) -> None:
        # "compute" is a real bug observed in omnimarket: not a runtime profile.
        path = _write(
            tmp_path,
            {
                "name": "node_demo_compute",
                "node_type": "compute",
                "runtime_profiles": ["compute"],
                "event_bus": {"subscribe_topics": ["onex.evt.demo.done.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        codes = {i.code for i in issues}
        assert RULE_RUNTIME_PROFILE_UNREGISTERED in codes
        unreg = next(i for i in issues if i.code == RULE_RUNTIME_PROFILE_UNREGISTERED)
        assert "'compute'" in unreg.message
        assert "unregistered" in unreg.message

    def test_descriptor_unregistered_profile_fails(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_orchestrator",
                "node_type": "orchestrator",
                "descriptor": {"runtime_profiles": ["does-not-exist"]},
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.start.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert RULE_RUNTIME_PROFILE_UNREGISTERED in {i.code for i in issues}

    def test_registered_profile_passes_unregistered_rule(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_orchestrator",
                "node_type": "orchestrator",
                "runtime_profiles": ["effects", "workers"],
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.start.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert RULE_RUNTIME_PROFILE_UNREGISTERED not in {i.code for i in issues}

    def test_mixed_registered_and_unregistered_reports_only_unknown(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_orchestrator",
                "node_type": "orchestrator",
                "runtime_profiles": ["main", "bogus"],
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.start.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        unreg = [i for i in issues if i.code == RULE_RUNTIME_PROFILE_UNREGISTERED]
        assert len(unreg) == 1
        assert "'bogus'" in unreg[0].message
        assert "'main'" not in unreg[0].message


@pytest.mark.unit
class TestValidatorRuntimeProfileNoConsumerLane:
    """OMN-12957: subscribing REDUCER/EFFECT must name a consumer-attached lane.

    The second class of silent orphaning: every named profile is registered but
    none runs a standalone consumer, so the subscriptions are never drained.
    """

    def test_effect_with_only_non_consumer_profile_fails(self, tmp_path: Path) -> None:
        # "canary" is registered but runs an isolated lane, not the effect
        # consumer group an EFFECT needs.
        path = _write(
            tmp_path,
            {
                "name": "node_demo_effect",
                "node_type": "effect",
                "runtime_profiles": ["canary"],
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.do.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        codes = {i.code for i in issues}
        assert RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE in codes
        finding = next(
            i for i in issues if i.code == RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE
        )
        assert "never drained" in finding.message

    def test_reducer_generic_with_non_consumer_profile_fails(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_reducer",
                "node_type": "REDUCER_GENERIC",
                "runtime_profiles": ["projection-api"],
                "event_bus": {"subscribe_topics": ["onex.evt.demo.happened.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE in {i.code for i in issues}

    def test_effect_with_consumer_profile_passes(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_effect",
                "node_type": "effect",
                "runtime_profiles": ["effects"],
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.do.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE not in {i.code for i in issues}

    def test_compute_with_non_consumer_profile_is_exempt(self, tmp_path: Path) -> None:
        # COMPUTE nodes do not own a standalone consumer lane; rule does not fire.
        path = _write(
            tmp_path,
            {
                "name": "node_demo_compute",
                "node_type": "compute",
                "runtime_profiles": ["canary"],
                "event_bus": {"subscribe_topics": ["onex.evt.demo.done.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE not in {i.code for i in issues}

    def test_effect_without_subscriptions_is_exempt(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_effect",
                "node_type": "effect",
                "runtime_profiles": ["canary"],
                "event_bus": {"publish_topics": ["onex.evt.demo.done.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(contract=_contract(), allowlist=set())
        issues = validator._validate_file(path, _contract())
        assert RULE_RUNTIME_PROFILE_NO_CONSUMER_LANE not in {i.code for i in issues}

    def test_allowlisted_node_exempt_from_consumer_lane_rule(
        self, tmp_path: Path
    ) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_demo_effect",
                "node_type": "effect",
                "runtime_profiles": ["canary"],
                "event_bus": {"subscribe_topics": ["onex.cmd.demo.do.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(
            contract=_contract(), allowlist={"node_demo_effect"}
        )
        issues = validator._validate_file(path, _contract())
        assert issues == ()


@pytest.mark.unit
class TestAllowlistFreezesAllRules:
    """A baselined (allowlisted) node is exempt from every runtime_profiles rule."""

    def test_allowlisted_unregistered_profile_is_frozen(self, tmp_path: Path) -> None:
        path = _write(
            tmp_path,
            {
                "name": "node_legacy_orphan",
                "node_type": "compute",
                "runtime_profiles": ["compute"],  # unregistered, but baselined
                "event_bus": {"subscribe_topics": ["onex.cmd.legacy.do.v1"]},
            },
        )
        validator = ValidatorRuntimeProfiles(
            contract=_contract(), allowlist={"node_legacy_orphan"}
        )
        issues = validator._validate_file(path, _contract())
        assert issues == ()


@pytest.mark.unit
class TestRegistryParity:
    """The core registry is the single source of truth for profile names."""

    def test_consumer_attached_is_subset_of_registered(self) -> None:
        from omnibase_core.constants.constants_runtime_profiles import (
            CONSUMER_ATTACHED_RUNTIME_PROFILES,
            REGISTERED_RUNTIME_PROFILES,
        )

        assert CONSUMER_ATTACHED_RUNTIME_PROFILES <= REGISTERED_RUNTIME_PROFILES


@pytest.mark.unit
class TestRepoBaselineAllowlistDiscovery:
    """OMN-12957: consumer repos vendor a frozen baseline discovered by path.

    A repo's baseline at ``<repo>/validation/runtime_profiles_allowlist.yaml`` is
    discovered by walking up from the scanned contract to the ``pyproject.toml``
    root. No env var. The effective allowlist is the union of core_default and repo_baseline.
    """

    def _make_repo(self, tmp_path: Path, baseline_node_ids: list[str]) -> Path:
        (tmp_path / "pyproject.toml").write_text(
            "[project]\nname='fake'\n", encoding="utf-8"
        )
        validation_dir = tmp_path / "validation"
        validation_dir.mkdir()
        entries = "\n".join(
            f"  - node_id: {nid}\n    reason: frozen baseline test entry"
            for nid in baseline_node_ids
        )
        (validation_dir / "runtime_profiles_allowlist.yaml").write_text(
            "allowlist:\n" + entries + "\n", encoding="utf-8"
        )
        node_dir = tmp_path / "src" / "nodes" / "node_demo"
        node_dir.mkdir(parents=True)
        return node_dir / "contract.yaml"

    def test_baselined_node_is_exempt(self, tmp_path: Path) -> None:
        contract_path = self._make_repo(tmp_path, ["node_demo_compute"])
        contract_path.write_text(
            yaml.safe_dump(
                {
                    "name": "node_demo_compute",
                    "node_type": "compute",
                    "runtime_profiles": ["compute"],  # unregistered
                    "event_bus": {"subscribe_topics": ["onex.evt.demo.done.v1"]},
                }
            ),
            encoding="utf-8",
        )
        # No explicit allowlist arg → repo discovery is active.
        validator = ValidatorRuntimeProfiles(contract=_contract())
        issues = validator._validate_file(contract_path, _contract())
        assert issues == ()

    def test_new_orphan_not_in_baseline_still_blocked(self, tmp_path: Path) -> None:
        contract_path = self._make_repo(tmp_path, ["some_other_node"])
        contract_path.write_text(
            yaml.safe_dump(
                {
                    "name": "node_demo_compute",
                    "node_type": "compute",
                    "runtime_profiles": ["compute"],  # unregistered, NOT baselined
                    "event_bus": {"subscribe_topics": ["onex.evt.demo.done.v1"]},
                }
            ),
            encoding="utf-8",
        )
        validator = ValidatorRuntimeProfiles(contract=_contract())
        issues = validator._validate_file(contract_path, _contract())
        assert RULE_RUNTIME_PROFILE_UNREGISTERED in {i.code for i in issues}
