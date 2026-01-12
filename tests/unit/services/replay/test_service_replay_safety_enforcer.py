# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ServiceReplaySafetyEnforcer - Runtime component for replay safety enforcement.

Tests cover:
- STRICT mode raises exception on non-deterministic effect
- WARN mode logs warning but continues
- PERMISSIVE mode allows with audit trail
- MOCKED mode injects mock values
- Classification for each source type (TIME, RANDOM, UUID, NETWORK, DATABASE, FILESYSTEM, ENVIRONMENT)
- Deterministic effects pass through all modes
- get_mock_value for each source type
- get_audit_trail returns all decisions
- reset() clears audit trail

OMN-1150: Replay Safety Enforcement

.. versionadded:: 0.6.3
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.replay.enum_effect_determinism import EnumEffectDeterminism
from omnibase_core.enums.replay.enum_enforcement_mode import EnumEnforcementMode
from omnibase_core.enums.replay.enum_non_deterministic_source import (
    EnumNonDeterministicSource,
)
from omnibase_core.errors import ModelOnexError
from omnibase_core.services.replay.service_replay_safety_enforcer import (
    ServiceReplaySafetyEnforcer,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def strict_enforcer() -> ServiceReplaySafetyEnforcer:
    """Create a STRICT mode enforcer."""
    return ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.STRICT)


@pytest.fixture
def warn_enforcer() -> ServiceReplaySafetyEnforcer:
    """Create a WARN mode enforcer."""
    return ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.WARN)


@pytest.fixture
def permissive_enforcer() -> ServiceReplaySafetyEnforcer:
    """Create a PERMISSIVE mode enforcer."""
    return ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)


@pytest.fixture
def mocked_enforcer() -> ServiceReplaySafetyEnforcer:
    """Create a MOCKED mode enforcer."""
    return ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.MOCKED)


# =============================================================================
# TEST STRICT MODE
# =============================================================================


@pytest.mark.unit
class TestStrictMode:
    """Tests for STRICT enforcement mode."""

    def test_strict_mode_blocks_non_deterministic_time_effect(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that STRICT mode blocks time-based effects."""
        with pytest.raises(ModelOnexError) as exc_info:
            strict_enforcer.enforce("time.now")

        assert exc_info.value.error_code == EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED
        assert "time" in str(exc_info.value.message).lower()

    def test_strict_mode_blocks_non_deterministic_random_effect(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that STRICT mode blocks random effects."""
        with pytest.raises(ModelOnexError) as exc_info:
            strict_enforcer.enforce("random.randint")

        assert exc_info.value.error_code == EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED

    def test_strict_mode_blocks_network_effect(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that STRICT mode blocks network effects."""
        with pytest.raises(ModelOnexError) as exc_info:
            strict_enforcer.enforce("http.get")

        assert exc_info.value.error_code == EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED
        assert "network" in str(exc_info.value.message).lower()

    def test_strict_mode_allows_deterministic_effect(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that STRICT mode allows deterministic effects."""
        decision = strict_enforcer.enforce("compute.hash")

        assert decision.decision == "allowed"
        assert decision.determinism == EnumEffectDeterminism.DETERMINISTIC

    def test_strict_mode_blocks_unknown_effect(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that STRICT mode blocks unknown effects."""
        with pytest.raises(ModelOnexError) as exc_info:
            strict_enforcer.enforce("custom.unknown.effect")

        assert exc_info.value.error_code == EnumCoreErrorCode.REPLAY_ENFORCEMENT_BLOCKED

    def test_strict_mode_records_blocked_decision_before_raising(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that blocked decision is recorded before raising."""
        try:
            strict_enforcer.enforce("time.now")
        except ModelOnexError:
            pass

        trail = strict_enforcer.get_audit_trail()
        assert len(trail) == 1
        assert trail[0].decision == "blocked"


# =============================================================================
# TEST WARN MODE
# =============================================================================


@pytest.mark.unit
class TestWarnMode:
    """Tests for WARN enforcement mode."""

    def test_warn_mode_warns_but_continues_for_time_effect(
        self, warn_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that WARN mode logs warning but continues."""
        decision = warn_enforcer.enforce("time.now")

        assert decision.decision == "warned"
        assert decision.determinism == EnumEffectDeterminism.NON_DETERMINISTIC
        assert decision.source == EnumNonDeterministicSource.TIME

    def test_warn_mode_warns_for_network_effect(
        self, warn_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that WARN mode warns for network effects."""
        decision = warn_enforcer.enforce("http.post")

        assert decision.decision == "warned"
        assert decision.source == EnumNonDeterministicSource.NETWORK

    def test_warn_mode_allows_deterministic_effect(
        self, warn_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that WARN mode allows deterministic effects without warning."""
        decision = warn_enforcer.enforce("transform.json")

        assert decision.decision == "allowed"
        assert decision.determinism == EnumEffectDeterminism.DETERMINISTIC

    def test_warn_mode_warns_for_unknown_effect(
        self, warn_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that WARN mode warns for unknown effects."""
        decision = warn_enforcer.enforce("unknown.effect")

        assert decision.decision == "warned"
        assert decision.determinism == EnumEffectDeterminism.UNKNOWN

    def test_warn_mode_records_warned_decisions(
        self, warn_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that warned decisions are recorded."""
        _ = warn_enforcer.enforce("time.now")
        _ = warn_enforcer.enforce("random.random")

        trail = warn_enforcer.get_audit_trail()
        assert len(trail) == 2
        assert all(d.decision == "warned" for d in trail)

    def test_warn_mode_with_custom_logger(self) -> None:
        """Test that WARN mode uses custom logger when provided."""
        mock_logger = MagicMock()
        enforcer = ServiceReplaySafetyEnforcer(
            mode=EnumEnforcementMode.WARN, logger=mock_logger
        )

        _ = enforcer.enforce("time.now")

        # ProtocolLoggerLike has warning() method for proper log level
        mock_logger.warning.assert_called()
        # Verify the message describes the non-deterministic effect
        call_args = mock_logger.warning.call_args
        assert "time.now" in call_args[0][0]


# =============================================================================
# TEST PERMISSIVE MODE
# =============================================================================


@pytest.mark.unit
class TestPermissiveMode:
    """Tests for PERMISSIVE enforcement mode."""

    def test_permissive_mode_allows_time_effect(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that PERMISSIVE mode allows time effects."""
        decision = permissive_enforcer.enforce("time.now")

        assert decision.decision == "allowed"
        assert decision.mode == EnumEnforcementMode.PERMISSIVE

    def test_permissive_mode_allows_network_effect(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that PERMISSIVE mode allows network effects."""
        decision = permissive_enforcer.enforce("http.get")

        assert decision.decision == "allowed"

    def test_permissive_mode_allows_database_effect(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that PERMISSIVE mode allows database effects."""
        decision = permissive_enforcer.enforce("db.query")

        assert decision.decision == "allowed"
        assert decision.source == EnumNonDeterministicSource.DATABASE

    def test_permissive_mode_records_audit_trail(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that PERMISSIVE mode records all decisions in audit trail."""
        _ = permissive_enforcer.enforce("time.now")
        _ = permissive_enforcer.enforce("http.get")
        _ = permissive_enforcer.enforce("compute.hash")

        trail = permissive_enforcer.get_audit_trail()
        assert len(trail) == 3

    def test_permissive_mode_allows_unknown_effect(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that PERMISSIVE mode allows unknown effects."""
        decision = permissive_enforcer.enforce("custom.effect")

        assert decision.decision == "allowed"
        assert decision.determinism == EnumEffectDeterminism.UNKNOWN


# =============================================================================
# TEST MOCKED MODE
# =============================================================================


@pytest.mark.unit
class TestMockedMode:
    """Tests for MOCKED enforcement mode."""

    def test_mocked_mode_returns_mocked_decision(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that MOCKED mode returns mocked decision."""
        decision = mocked_enforcer.enforce("time.now")

        assert decision.decision == "mocked"
        assert decision.mock_injected is True
        assert decision.mocked_value is not None

    def test_mocked_mode_injects_time_mock(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that MOCKED mode injects time mock."""
        decision = mocked_enforcer.enforce("datetime.now")

        assert decision.mock_injected is True
        assert isinstance(decision.mocked_value, datetime)

    def test_mocked_mode_injects_random_mock(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that MOCKED mode injects random mock."""
        decision = mocked_enforcer.enforce("random.random")

        assert decision.mock_injected is True
        assert decision.mocked_value == 0.5  # Default deterministic value

    def test_mocked_mode_injects_uuid_mock(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that MOCKED mode injects UUID mock."""
        decision = mocked_enforcer.enforce("uuid.uuid4")

        assert decision.mock_injected is True
        assert isinstance(decision.mocked_value, UUID)

    def test_mocked_mode_allows_deterministic_effect_without_mocking(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that MOCKED mode allows deterministic effects without mocking."""
        decision = mocked_enforcer.enforce("compute.hash")

        assert decision.decision == "allowed"
        assert decision.mock_injected is False

    def test_mocked_mode_with_time_injector(self) -> None:
        """Test MOCKED mode uses provided time injector."""
        from omnibase_core.services.replay.injector_time import InjectorTime

        fixed_time = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
        time_injector = InjectorTime(fixed_time=fixed_time)
        enforcer = ServiceReplaySafetyEnforcer(
            mode=EnumEnforcementMode.MOCKED, time_injector=time_injector
        )

        decision = enforcer.enforce("time.now")

        assert decision.mocked_value == fixed_time


# =============================================================================
# TEST EFFECT CLASSIFICATION
# =============================================================================


@pytest.mark.unit
class TestEffectClassification:
    """Tests for effect type classification."""

    def test_classify_time_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of time-based effects."""
        for effect in ["time.now", "time.time", "datetime.now", "clock.monotonic"]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.NON_DETERMINISTIC
            assert source == EnumNonDeterministicSource.TIME

    def test_classify_random_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of random effects."""
        for effect in ["random.random", "random.randint", "secrets.token_hex"]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.NON_DETERMINISTIC
            assert source == EnumNonDeterministicSource.RANDOM

    def test_classify_uuid_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of UUID effects."""
        for effect in ["uuid.uuid4", "uuid.uuid1"]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.NON_DETERMINISTIC
            assert source == EnumNonDeterministicSource.UUID

    def test_classify_network_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of network effects."""
        for effect in ["http.get", "https.post", "network.request", "api.call"]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.NON_DETERMINISTIC
            assert source == EnumNonDeterministicSource.NETWORK

    def test_classify_database_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of database effects."""
        for effect in ["db.query", "database.execute", "sql.select", "postgres.fetch"]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.NON_DETERMINISTIC
            assert source == EnumNonDeterministicSource.DATABASE

    def test_classify_filesystem_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of filesystem effects."""
        for effect in ["file.read", "fs.write", "path.exists", "io.open"]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.NON_DETERMINISTIC
            assert source == EnumNonDeterministicSource.FILESYSTEM

    def test_classify_environment_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of environment effects."""
        for effect in ["env.get", "environ.read", "config.load", "settings.get"]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.NON_DETERMINISTIC
            assert source == EnumNonDeterministicSource.ENVIRONMENT

    def test_classify_deterministic_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of deterministic effects."""
        for effect in [
            "compute.hash",
            "transform.json",
            "parse.yaml",
            "validate.schema",
            "hash.sha256",
            "encode.base64",
        ]:
            determinism, source = strict_enforcer.classify_effect(effect)
            assert determinism == EnumEffectDeterminism.DETERMINISTIC
            assert source is None

    def test_classify_unknown_effects(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test classification of unknown effects."""
        determinism, source = strict_enforcer.classify_effect("custom.unknown")
        assert determinism == EnumEffectDeterminism.UNKNOWN
        assert source is None

    def test_classification_is_case_insensitive(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that classification is case-insensitive."""
        determinism1, source1 = strict_enforcer.classify_effect("TIME.NOW")
        determinism2, source2 = strict_enforcer.classify_effect("time.now")

        assert determinism1 == determinism2
        assert source1 == source2


# =============================================================================
# TEST GET_MOCK_VALUE
# =============================================================================


@pytest.mark.unit
class TestGetMockValue:
    """Tests for get_mock_value method."""

    def test_get_mock_value_time(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test get_mock_value for TIME source."""
        value = mocked_enforcer.get_mock_value(EnumNonDeterministicSource.TIME)
        assert isinstance(value, datetime)

    def test_get_mock_value_random(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test get_mock_value for RANDOM source."""
        value = mocked_enforcer.get_mock_value(EnumNonDeterministicSource.RANDOM)
        assert value == 0.5

    def test_get_mock_value_uuid(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test get_mock_value for UUID source."""
        value = mocked_enforcer.get_mock_value(EnumNonDeterministicSource.UUID)
        assert isinstance(value, UUID)

    def test_get_mock_value_network(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test get_mock_value for NETWORK source."""
        value = mocked_enforcer.get_mock_value(EnumNonDeterministicSource.NETWORK)
        assert value == {}

    def test_get_mock_value_database(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test get_mock_value for DATABASE source."""
        value = mocked_enforcer.get_mock_value(EnumNonDeterministicSource.DATABASE)
        assert value == {}

    def test_get_mock_value_filesystem(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test get_mock_value for FILESYSTEM source."""
        value = mocked_enforcer.get_mock_value(EnumNonDeterministicSource.FILESYSTEM)
        assert value == ""

    def test_get_mock_value_environment(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test get_mock_value for ENVIRONMENT source."""
        value = mocked_enforcer.get_mock_value(EnumNonDeterministicSource.ENVIRONMENT)
        assert value == ""

    def test_get_mock_value_with_custom_injectors(self) -> None:
        """Test get_mock_value uses custom injectors when provided."""
        from omnibase_core.services.replay.injector_rng import InjectorRNG
        from omnibase_core.services.replay.injector_time import InjectorTime

        from omnibase_core.enums.replay.enum_recorder_mode import EnumRecorderMode
        from omnibase_core.services.replay.injector_uuid import InjectorUUID

        fixed_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        time_injector = InjectorTime(fixed_time=fixed_time)
        rng_injector = InjectorRNG(seed=42)

        sample_uuid = UUID("550e8400-e29b-41d4-a716-446655440001")
        uuid_injector = InjectorUUID(
            mode=EnumRecorderMode.REPLAYING, recorded_uuids=[sample_uuid]
        )

        enforcer = ServiceReplaySafetyEnforcer(
            mode=EnumEnforcementMode.MOCKED,
            time_injector=time_injector,
            rng_injector=rng_injector,
            uuid_injector=uuid_injector,
        )

        assert enforcer.get_mock_value(EnumNonDeterministicSource.TIME) == fixed_time
        assert enforcer.get_mock_value(EnumNonDeterministicSource.UUID) == sample_uuid

    def test_get_mock_value_time_fallback_is_deterministic(self) -> None:
        """Test that TIME fallback returns deterministic epoch when no injector."""
        enforcer1 = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.MOCKED)
        enforcer2 = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.MOCKED)

        value1 = enforcer1.get_mock_value(EnumNonDeterministicSource.TIME)
        value2 = enforcer2.get_mock_value(EnumNonDeterministicSource.TIME)

        # Values should be identical (deterministic)
        assert value1 == value2
        # Should be Unix epoch (1970-01-01 00:00:00 UTC)
        assert value1 == datetime(1970, 1, 1, tzinfo=UTC)
        assert value1.year == 1970
        assert value1.month == 1
        assert value1.day == 1

    def test_get_mock_value_uuid_fallback_is_deterministic(self) -> None:
        """Test that UUID fallback returns deterministic value when no injector."""
        enforcer1 = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.MOCKED)
        enforcer2 = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.MOCKED)

        value1 = enforcer1.get_mock_value(EnumNonDeterministicSource.UUID)
        value2 = enforcer2.get_mock_value(EnumNonDeterministicSource.UUID)

        # Values should be identical (deterministic)
        assert value1 == value2
        # Should be the fixed deterministic UUID
        assert value1 == UUID("00000000-0000-4000-8000-000000000000")


# =============================================================================
# TEST AUDIT TRAIL
# =============================================================================


@pytest.mark.unit
class TestAuditTrail:
    """Tests for audit trail functionality."""

    def test_get_audit_trail_empty_initially(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that audit trail is empty initially."""
        trail = permissive_enforcer.get_audit_trail()
        assert trail == []

    def test_get_audit_trail_returns_all_decisions(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that audit trail contains all decisions."""
        _ = permissive_enforcer.enforce("time.now")
        _ = permissive_enforcer.enforce("http.get")
        _ = permissive_enforcer.enforce("compute.hash")

        trail = permissive_enforcer.get_audit_trail()
        assert len(trail) == 3

    def test_get_audit_trail_returns_copy(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that get_audit_trail returns a copy."""
        _ = permissive_enforcer.enforce("time.now")

        trail1 = permissive_enforcer.get_audit_trail()
        trail2 = permissive_enforcer.get_audit_trail()

        assert trail1 == trail2
        assert trail1 is not trail2

    def test_audit_trail_preserves_order(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that audit trail preserves decision order."""
        effect_types = ["time.now", "http.get", "db.query", "compute.hash"]

        for effect_type in effect_types:
            _ = permissive_enforcer.enforce(effect_type)

        trail = permissive_enforcer.get_audit_trail()
        for i, effect_type in enumerate(effect_types):
            assert trail[i].effect_type == effect_type

    def test_audit_count_property(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test audit_count property."""
        assert permissive_enforcer.audit_count == 0

        _ = permissive_enforcer.enforce("time.now")
        assert permissive_enforcer.audit_count == 1

        _ = permissive_enforcer.enforce("http.get")
        assert permissive_enforcer.audit_count == 2


# =============================================================================
# TEST RESET
# =============================================================================


@pytest.mark.unit
class TestReset:
    """Tests for reset functionality."""

    def test_reset_clears_audit_trail(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that reset clears the audit trail."""
        _ = permissive_enforcer.enforce("time.now")
        _ = permissive_enforcer.enforce("http.get")
        assert permissive_enforcer.audit_count == 2

        permissive_enforcer.reset()

        assert permissive_enforcer.audit_count == 0
        assert permissive_enforcer.get_audit_trail() == []

    def test_reset_allows_new_session(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that reset allows starting a new session."""
        _ = permissive_enforcer.enforce("time.now")
        permissive_enforcer.reset()

        _ = permissive_enforcer.enforce("http.get")

        trail = permissive_enforcer.get_audit_trail()
        assert len(trail) == 1
        assert trail[0].effect_type == "http.get"


# =============================================================================
# TEST MODE PROPERTY
# =============================================================================


@pytest.mark.unit
class TestModeProperty:
    """Tests for mode property."""

    def test_mode_property_strict(
        self, strict_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test mode property for STRICT enforcer."""
        assert strict_enforcer.mode == EnumEnforcementMode.STRICT

    def test_mode_property_warn(
        self, warn_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test mode property for WARN enforcer."""
        assert warn_enforcer.mode == EnumEnforcementMode.WARN

    def test_mode_property_permissive(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test mode property for PERMISSIVE enforcer."""
        assert permissive_enforcer.mode == EnumEnforcementMode.PERMISSIVE

    def test_mode_property_mocked(
        self, mocked_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test mode property for MOCKED enforcer."""
        assert mocked_enforcer.mode == EnumEnforcementMode.MOCKED

    def test_default_mode_is_strict(self) -> None:
        """Test that default mode is STRICT."""
        enforcer = ServiceReplaySafetyEnforcer()
        assert enforcer.mode == EnumEnforcementMode.STRICT


# =============================================================================
# TEST DECISION MODEL
# =============================================================================


@pytest.mark.unit
class TestDecisionModel:
    """Tests for ModelEnforcementDecision fields."""

    def test_decision_has_timestamp(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that decision has timestamp."""
        decision = permissive_enforcer.enforce("time.now")
        assert decision.timestamp is not None
        assert isinstance(decision.timestamp, datetime)

    def test_decision_has_reason(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that decision has reason."""
        decision = permissive_enforcer.enforce("time.now")
        assert decision.reason is not None
        assert len(decision.reason) > 0

    def test_decision_records_mode(
        self, permissive_enforcer: ServiceReplaySafetyEnforcer
    ) -> None:
        """Test that decision records the enforcement mode."""
        decision = permissive_enforcer.enforce("time.now")
        assert decision.mode == EnumEnforcementMode.PERMISSIVE


# =============================================================================
# TEST PROTOCOL COMPLIANCE
# =============================================================================


@pytest.mark.unit
class TestProtocolCompliance:
    """Tests for ProtocolReplaySafetyEnforcer compliance."""

    def test_implements_enforce(self) -> None:
        """Test that ServiceReplaySafetyEnforcer implements enforce()."""
        enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)
        decision = enforcer.enforce("test.effect")
        assert decision is not None

    def test_implements_classify_effect(self) -> None:
        """Test that ServiceReplaySafetyEnforcer implements classify_effect()."""
        enforcer = ServiceReplaySafetyEnforcer()
        determinism, _source = enforcer.classify_effect("time.now")
        assert determinism is not None

    def test_protocol_check_at_module_load(self) -> None:
        """Test that protocol compliance is verified at module load."""
        from omnibase_core.protocols.replay.protocol_replay_safety_enforcer import (
            ProtocolReplaySafetyEnforcer,
        )

        enforcer = ServiceReplaySafetyEnforcer()
        _check: ProtocolReplaySafetyEnforcer = enforcer
        assert _check is not None
