# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The preset and default timings are a packaged contract, not literals in code (OMN-21796)."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.models.cli.model_cli_execution_resources import (
    ModelCliExecutionResources,
)
from omnibase_core.models.dedup.model_action_dedup_base import ModelActionDedupBase
from omnibase_core.models.health.model_health_metadata import ModelHealthMetadata
from omnibase_core.models.infrastructure.model_compute_cache import ModelComputeCache
from omnibase_core.models.runtime import model_service_timings
from omnibase_core.models.runtime.model_runtime_aliveness_probe import (
    DEFAULT_TIMEOUT_SECONDS,
)
from omnibase_core.models.runtime.model_service_timings import (
    ModelServiceTimings,
    packaged_service_timings,
)
from omnibase_core.models.security.model_session_policy import ModelSessionPolicy
from omnibase_core.models.security.model_trustpolicy import ModelTrustPolicy
from omnibase_core.validation.validator_contracts_and_di import (
    ValidatorContractsAndDi,
)

_CONTRACT = Path(model_service_timings.__file__).with_name("service_timings.yaml")
_PACKAGE = Path(model_service_timings.__file__).parents[2]

# The timings the modules carried as literals before the contract held them.
_PREVIOUS_LITERALS: dict[str, float] = {
    "session_minimal_idle_minutes": 120,
    "session_strict_idle_minutes": 15,
    "session_strict_fresh_auth_minutes": 3,
    "session_maximum_idle_minutes": 10,
    "session_maximum_absolute_minutes": 120,
    "session_maximum_fresh_auth_minutes": 1,
    "session_maximum_warn_before_minutes": 2,
    "health_production_check_interval_seconds": 30,
    "health_development_check_interval_seconds": 60,
    "health_maintenance_check_interval_seconds": 120,
    "cli_limited_wait_seconds": 300,
    "cli_quick_wait_seconds": 30,
    "database_service_connection_wait_seconds": 30,
    "database_service_health_check_wait_seconds": 5,
    "file_destination_flush_interval_ms": 5000,
    "kafka_destination_flush_interval_ms": 1000,
    "dedup_default_ttl_hours": 6,
    "discover_tools_wait_seconds": 5.0,
    "high_priority_input_wait_seconds": 60,
    "output_retry_delay_seconds": 30,
    "compute_cache_default_ttl_minutes": 30,
    "node_execution_default_wait_seconds": 300,
    "replay_retry_delay_ms": 100.0,
    "aliveness_probe_wait_seconds": 30,
    "restricted_connection_wait_seconds": 10,
    "secret_cache_ttl_seconds": 300,
    "trust_policy_max_cache_ttl_seconds": 86400,
}

_SOURCES_WITHOUT_TIMEOUT_LITERALS = [
    "models/security/model_session_policy.py",
    "models/health/model_health_metadata.py",
    "models/cli/model_cli_execution_resources.py",
    "models/services/model_external_service_config.py",
    "models/validation/model_event_destination.py",
    "models/dedup/model_action_dedup_base.py",
    "models/discovery/model_discovery_request.py",
    "models/event_bus/model_event_bus_input_state.py",
    "models/event_bus/model_event_bus_output_state.py",
    "models/infrastructure/model_compute_cache.py",
    "models/node_metadata/model_node_execution_settings.py",
    "models/replay/model_corpus_replay_config.py",
    "models/runtime/model_runtime_aliveness_probe.py",
    "models/security/model_network_restrictions.py",
    "models/security/model_secret_config.py",
    "models/security/model_trustpolicy.py",
]


@pytest.mark.unit
class TestServiceTimingsContract:
    def test_packaged_contract_carries_the_previous_timings(self) -> None:
        assert ModelServiceTimings.packaged().model_dump() == _PREVIOUS_LITERALS

    def test_every_model_field_is_declared_in_the_contract(self) -> None:
        declared = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
        assert set(declared) == set(ModelServiceTimings.model_fields)

    def test_a_missing_timing_fails_to_load(self) -> None:
        partial = dict(_PREVIOUS_LITERALS)
        del partial["secret_cache_ttl_seconds"]
        with pytest.raises(ValidationError, match="secret_cache_ttl_seconds"):
            ModelServiceTimings.model_validate(partial)

    def test_an_unknown_timing_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="not_a_timing"):
            ModelServiceTimings.model_validate(
                {**_PREVIOUS_LITERALS, "not_a_timing": 1}
            )

    def test_a_non_positive_timing_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="dedup_default_ttl_hours"):
            ModelServiceTimings.model_validate(
                {**_PREVIOUS_LITERALS, "dedup_default_ttl_hours": 0}
            )


@pytest.mark.unit
class TestTimingsReachCallSites:
    def test_session_presets_keep_their_previous_values(self) -> None:
        minimal = ModelSessionPolicy.create_minimal()
        strict = ModelSessionPolicy.create_strict()
        maximum = ModelSessionPolicy.create_maximum()
        assert minimal.idle_timeout_minutes == 120
        assert (strict.idle_timeout_minutes, strict.fresh_auth_timeout_minutes) == (
            15,
            3,
        )
        assert (
            maximum.idle_timeout_minutes,
            maximum.absolute_timeout_minutes,
            maximum.fresh_auth_timeout_minutes,
            maximum.warn_before_timeout_minutes,
        ) == (10, 120, 1, 2)

    def test_health_presets_keep_their_previous_intervals(self) -> None:
        assert ModelHealthMetadata.create_production().check_interval_seconds == 30
        assert ModelHealthMetadata.create_development().check_interval_seconds == 60
        assert (
            ModelHealthMetadata.create_maintenance_mode().check_interval_seconds == 120
        )

    def test_cli_resources_default_to_the_contract_and_explicit_wins(self) -> None:
        assert ModelCliExecutionResources.create_limited().timeout_seconds == 300
        assert (
            ModelCliExecutionResources.create_limited(timeout_seconds=7).timeout_seconds
            == 7
        )
        assert ModelCliExecutionResources.create_quick().timeout_seconds == 30

    def test_constants_are_read_from_the_contract(self) -> None:
        timings = packaged_service_timings()
        assert timings.dedup_default_ttl_hours == ModelActionDedupBase.DEFAULT_TTL_HOURS
        assert timings.aliveness_probe_wait_seconds == DEFAULT_TIMEOUT_SECONDS
        assert (
            timings.trust_policy_max_cache_ttl_seconds
            == ModelTrustPolicy.MAX_CACHE_TTL_SECONDS
        )

    def test_compute_cache_default_ttl_comes_from_the_contract(self) -> None:
        assert ModelComputeCache().default_ttl_minutes == 30
        assert ModelComputeCache(default_ttl_minutes=5).default_ttl_minutes == 5


@pytest.mark.unit
class TestSourcesDrawNoTimeoutLiteralFinding:
    @pytest.mark.parametrize("relative", _SOURCES_WITHOUT_TIMEOUT_LITERALS)
    def test_source_yields_no_literal_timeout_finding(self, relative: str) -> None:
        source = _PACKAGE / relative
        assert source.is_file()
        result = ValidatorContractsAndDi().validate_file(source)
        assert [i.message for i in result.issues if i.code == "literal_timeout"] == []

    def test_the_checker_still_flags_a_planted_timeout_literal(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / ".git").mkdir()
        planted = tmp_path / "planted.py"
        planted.write_text("def run(client):\n    return client.get(timeout=5)\n")
        result = ValidatorContractsAndDi().validate_file(planted)
        assert [i.code for i in result.issues if i.code == "literal_timeout"] == [
            "literal_timeout"
        ]
