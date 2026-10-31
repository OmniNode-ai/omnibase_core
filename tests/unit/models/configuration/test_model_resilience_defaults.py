# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The resilience defaults contract binds every timing the resilience presets fall back to (OMN-21740)."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType

import pytest
from pydantic import ValidationError
from ruamel.yaml import YAML

from omnibase_core.models.configuration import (
    model_circuit_breaker,
    model_resilience_defaults,
    model_throttling_behavior,
)
from omnibase_core.models.configuration.model_circuit_breaker import ModelCircuitBreaker
from omnibase_core.models.configuration.model_resilience_defaults import (
    ModelResilienceDefaults,
)
from omnibase_core.models.configuration.model_throttling_behavior import (
    ModelThrottlingBehavior,
)
from omnibase_core.models.connections import model_connection_pool
from omnibase_core.models.connections.model_connection_pool import ModelConnectionPool
from omnibase_core.models.core import model_retry_config
from omnibase_core.models.core.model_retry_config import ModelRetryConfig
from omnibase_core.models.infrastructure import model_retry_advanced, model_retry_policy
from omnibase_core.models.infrastructure.model_retry_advanced import (
    ModelRetryAdvanced,
)
from omnibase_core.models.infrastructure.model_retry_policy import ModelRetryPolicy
from omnibase_core.validation.validator_contracts_and_di import ValidatorContractsAndDi

CONTRACT = Path(model_resilience_defaults.__file__).with_name(
    "resilience_defaults.yaml"
)


def _declared() -> dict[str, object]:
    with CONTRACT.open(encoding="utf-8") as contract:
        document = YAML(typ="safe").load(contract)
    assert isinstance(document, dict)
    return document


@pytest.mark.unit
class TestResilienceDefaultsContract:
    def test_packaged_contract_loads_and_matches_the_yaml(self) -> None:
        loaded = ModelResilienceDefaults.load()
        assert loaded.model_dump(exclude_none=True) == _declared()

    def test_load_is_read_once(self) -> None:
        assert ModelResilienceDefaults.load() is ModelResilienceDefaults.load()

    def test_unknown_key_is_refused(self) -> None:
        declared = _declared()
        declared["retry_config"] = {"stray": 1}
        with pytest.raises(ValidationError):
            ModelResilienceDefaults.model_validate(declared)

    def test_negative_timing_is_refused(self) -> None:
        declared = _declared()
        declared["circuit_breaker"] = {
            "fast_fail_open_seconds": -1,
            "resilient_open_seconds": 120,
        }
        with pytest.raises(ValidationError):
            ModelResilienceDefaults.model_validate(declared)


@pytest.mark.unit
class TestPresetsReadTheContract:
    def test_retry_config_presets(self) -> None:
        d = ModelResilienceDefaults.load().retry_config
        for config, preset in (
            (ModelRetryConfig.create_conservative(), d.conservative),
            (ModelRetryConfig.create_standard(), d.standard),
            (ModelRetryConfig.create_aggressive(), d.aggressive),
            (ModelRetryConfig.create_fast_fail(), d.fast_fail),
        ):
            assert config.max_attempts == preset.max_attempts
            assert config.backoff_seconds == preset.backoff_seconds
        assert (
            ModelRetryConfig.create_linear().backoff_seconds == d.linear_backoff_seconds
        )

    def test_injected_value_wins_over_the_contract(self) -> None:
        assert (
            ModelRetryConfig.create_linear(backoff_seconds=9.0).backoff_seconds == 9.0
        )
        assert (
            ModelRetryPolicy.create_fixed_delay(delay=7.0).config.backoff_seconds == 7.0
        )
        assert (
            ModelRetryAdvanced.create_with_circuit_breaker(
                reset_timeout=11.0
            ).circuit_breaker_reset_seconds
            == 11.0
        )

    def test_retry_policy_factories(self) -> None:
        d = ModelResilienceDefaults.load().retry_policy
        assert (
            ModelRetryPolicy.create_exponential_backoff().config.backoff_seconds
            == d.base_delay_seconds
        )
        assert (
            ModelRetryPolicy.create_fixed_delay().config.backoff_seconds
            == d.fixed_delay_seconds
        )
        assert (
            ModelRetryPolicy.create_for_http().config.backoff_seconds
            == d.http_base_delay_seconds
        )
        assert (
            ModelRetryPolicy.create_for_database().config.backoff_seconds
            == d.database_base_delay_seconds
        )
        policy = ModelRetryPolicy.create_with_circuit_breaker()
        assert policy.advanced.circuit_breaker_reset_seconds == (
            d.circuit_breaker_reset_seconds
        )

    def test_circuit_breaker_presets(self) -> None:
        d = ModelResilienceDefaults.load().circuit_breaker
        assert (
            ModelCircuitBreaker.create_fast_fail().timeout_seconds
            == d.fast_fail_open_seconds
        )
        assert (
            ModelCircuitBreaker.create_resilient().timeout_seconds
            == d.resilient_open_seconds
        )

    def test_throttling_presets(self) -> None:
        d = ModelResilienceDefaults.load().throttling
        graceful = ModelThrottlingBehavior.create_graceful_delay()
        assert graceful.base_delay_ms == d.graceful_delay.base_delay_ms
        assert graceful.max_delay_ms == d.graceful_delay.max_delay_ms
        assert graceful.delay_multiplier == d.graceful_delay_multiplier
        adaptive = ModelThrottlingBehavior.create_adaptive_throttling()
        assert adaptive.base_delay_ms == d.adaptive.base_delay_ms
        assert adaptive.max_delay_ms == d.adaptive.max_delay_ms
        assert (
            ModelThrottlingBehavior.create_queue_based().queue_wait_seconds
            == d.queue_wait_seconds
        )

    @pytest.mark.parametrize(
        "factory",
        [
            "create_single_connection",
            "create_small_pool",
            "create_large_pool",
            "create_aggressive_retry",
            "create_quick_timeout",
        ],
    )
    def test_connection_pool_presets(self, factory: str) -> None:
        preset = getattr(ModelResilienceDefaults.load().connection_pool, factory[7:])
        pool = getattr(ModelConnectionPool, factory)()
        assert pool.timeout_seconds == preset.operation_seconds
        assert pool.retry_delay_seconds == preset.retry_delay_seconds
        assert pool.pool_timeout == preset.pool_wait_seconds


_TOUCHED_MODULES = (
    model_circuit_breaker,
    model_throttling_behavior,
    model_connection_pool,
    model_retry_config,
    model_retry_advanced,
    model_retry_policy,
)


@pytest.mark.unit
class TestCheckerReportsNoTimeoutLiteral:
    @pytest.mark.parametrize("module", _TOUCHED_MODULES, ids=lambda m: m.__name__)
    def test_module_holds_no_timeout_literal(self, module: ModuleType) -> None:
        assert module.__file__ is not None
        result = ValidatorContractsAndDi().validate_file(Path(module.__file__))
        assert [
            f"{i.line_number}: {i.message}"
            for i in result.issues
            if i.code == "literal_timeout"
        ] == []

    def test_checker_still_flags_a_planted_literal(self, tmp_path: Path) -> None:
        planted = tmp_path / "src" / "omnibase_core" / "planted_timeout.py"
        planted.parent.mkdir(parents=True)
        planted.write_text("REQUEST_TIMEOUT_SECONDS = 17\n")
        (tmp_path / ".git").mkdir()
        result = ValidatorContractsAndDi().validate_file(planted)
        assert "literal_timeout" in {i.code for i in result.issues}
