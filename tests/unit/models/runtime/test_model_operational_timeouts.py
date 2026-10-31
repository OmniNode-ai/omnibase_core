# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""The operational timeouts are a packaged contract, not literals in code (OMN-21623)."""

import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
import yaml
from pydantic import ValidationError

from omnibase_core.adapters import merge_strategy_detector, rebase_handler
from omnibase_core.adapters.merge_strategy_detector import MergeStrategyDetector
from omnibase_core.models.discovery.model_request_introspection_event import (
    ModelRequestIntrospectionEvent,
)
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.health.model_health_check_config import ModelHealthCheckConfig
from omnibase_core.models.runtime import model_operational_timeouts
from omnibase_core.models.runtime.model_operational_timeouts import (
    ModelOperationalTimeouts,
)
from omnibase_core.validation.validator_contracts_and_di import (
    ValidatorContractsAndDi,
)

_CONTRACT = Path(model_operational_timeouts.__file__).with_name(
    "operational_timeouts.yaml"
)

# The budgets the modules carried as literals before the contract held them.
_PREVIOUS_LITERALS = {
    "merge_queue_enqueue_seconds": 10.0,
    "merge_strategy_api_seconds": 10.0,
    "rebase_run_seconds": 60.0,
    "rebase_fetch_seconds": 30.0,
    "rebase_abort_seconds": 10.0,
    "work_ledger_lock_seconds": 30.0,
    "occ_git_read_seconds": 10.0,
    "occ_formatter_version_seconds": 5.0,
    "occ_formatter_lint_seconds": 10.0,
    "receipt_reprobe_reexec_seconds": 120.0,
    "contracts_validation_seconds": 300.0,
    "consumer_graph_lock_seconds": 60.0,
    "shared_token_policy_response_seconds": 5.0,
    "introspection_discovery_seconds": 5.0,
    "introspection_mcp_discovery_seconds": 3.0,
    "introspection_health_check_seconds": 2.0,
    "tool_invocation_mcp_seconds": 10.0,
    "tool_invocation_cli_seconds": 60.0,
}

_SOURCES_WITHOUT_TIMEOUT_LITERALS = [
    "adapters/github_merge_queue_adapter.py",
    "adapters/merge_strategy_detector.py",
    "adapters/rebase_handler.py",
    "models/discovery/model_request_introspection_event.py",
    "models/discovery/model_tool_invocation_event.py",
    "models/health/model_health_check_config.py",
    "analysis/consumer_graph.py",
    "cli/cli_work_ledger_render.py",
    "nodes/node_source_file_gather_effect/runtime_shared_token_policy.py",
    "validation/validator_contracts.py",
    "validation/validator_occ_merge_eligibility.py",
    "validation/validator_receipt_reprobe.py",
]


@pytest.mark.unit
class TestOperationalTimeoutsContract:
    def test_packaged_contract_carries_the_previous_budgets(self) -> None:
        packaged = ModelOperationalTimeouts.packaged()
        assert packaged.model_dump() == _PREVIOUS_LITERALS

    def test_every_model_field_is_declared_in_the_contract(self) -> None:
        declared = yaml.safe_load(_CONTRACT.read_text(encoding="utf-8"))
        assert set(declared) == set(ModelOperationalTimeouts.model_fields)

    def test_a_missing_budget_fails_to_load(self) -> None:
        partial = dict(_PREVIOUS_LITERALS)
        del partial["rebase_run_seconds"]
        with pytest.raises(ValidationError, match="rebase_run_seconds"):
            ModelOperationalTimeouts.model_validate(partial)

    def test_an_unknown_budget_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="not_a_budget"):
            ModelOperationalTimeouts.model_validate(
                {**_PREVIOUS_LITERALS, "not_a_budget": 1.0}
            )

    def test_a_non_positive_budget_is_refused(self) -> None:
        with pytest.raises(ValidationError, match="inference_curl_seconds"):
            ModelOperationalTimeouts.model_validate(
                {**_PREVIOUS_LITERALS, "inference_curl_seconds": 0}
            )


@pytest.mark.unit
class TestOperationalTimeoutsReachCallSites:
    def test_a_merge_strategy_probe_runs_under_the_declared_budget(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake_run(*_args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            seen.update(kwargs)
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr=""
            )

        monkeypatch.setattr(subprocess, "run", fake_run)
        MergeStrategyDetector.clear_cache()
        MergeStrategyDetector("o", "r").detect()
        assert seen["timeout"] == _PREVIOUS_LITERALS["merge_strategy_api_seconds"]

    def test_a_merge_strategy_probe_follows_an_overlaid_budget(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: dict[str, Any] = {}

        def fake_run(*_args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            seen.update(kwargs)
            return subprocess.CompletedProcess(
                args=[], returncode=1, stdout="", stderr=""
            )

        overlaid = ModelOperationalTimeouts.packaged().model_copy(
            update={"merge_strategy_api_seconds": 7.5}
        )
        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(
            merge_strategy_detector, "packaged_timeouts", lambda: overlaid
        )
        MergeStrategyDetector.clear_cache()
        MergeStrategyDetector("o", "r").detect()
        assert seen["timeout"] == 7.5

    def test_a_rebase_uses_the_declared_fetch_and_run_budgets(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        budgets: list[float] = []

        def fake_run(*_args: object, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            budgets.append(kwargs["timeout"])
            return subprocess.CompletedProcess(
                args=[], returncode=0, stdout="", stderr=""
            )

        monkeypatch.setattr(rebase_handler.subprocess, "run", fake_run)
        assert rebase_handler.attempt_rebase(tmp_path, "feature").success
        assert budgets == [
            _PREVIOUS_LITERALS["rebase_fetch_seconds"],
            _PREVIOUS_LITERALS["rebase_run_seconds"],
        ]


@pytest.mark.unit
class TestDiscoveryFactoryDefaults:
    """The factories' default waits come from the contract and keep their previous millisecond values."""

    def test_introspection_request_defaults(self) -> None:
        assert (
            ModelRequestIntrospectionEvent.create_discovery_request(
                requester_id=uuid4()
            ).timeout_ms
            == 5000
        )
        assert (
            ModelRequestIntrospectionEvent.create_mcp_discovery_request().timeout_ms
            == 3000
        )
        assert (
            ModelRequestIntrospectionEvent.create_health_check_request().timeout_ms
            == 2000
        )

    def test_tool_invocation_defaults(self) -> None:
        mcp = ModelToolInvocationEvent.create_mcp_tool_invocation(
            target_node_name="n", tool_name="t", action="a"
        )
        cli = ModelToolInvocationEvent.create_cli_tool_invocation(
            target_node_name="n", tool_name="t", action="a"
        )
        assert (mcp.timeout_ms, cli.timeout_ms) == (10000, 60000)

    def test_an_explicit_wait_is_kept(self) -> None:
        event = ModelRequestIntrospectionEvent.create_health_check_request(
            timeout_ms=1234
        )
        assert event.timeout_ms == 1234


@pytest.mark.unit
class TestPresetContracts:
    """Health-check presets are packaged YAML, not constructor literals."""

    def test_production_health_checks_come_from_their_packaged_preset(self) -> None:
        production = ModelHealthCheckConfig.create_production_checks()
        assert (production.check_interval_seconds, production.timeout_seconds) == (
            30,
            5,
        )
        assert production.check_headers == {
            "X-Health-Check": "load-balancer",
            "X-Environment": "production",
        }

    def test_a_preset_is_independent_of_the_cached_mapping(self) -> None:
        first = ModelHealthCheckConfig.create_production_checks()
        assert first.check_headers is not None
        first.check_headers["X-Environment"] = "changed"
        again = ModelHealthCheckConfig.create_production_checks()
        assert again.check_headers == {
            "X-Health-Check": "load-balancer",
            "X-Environment": "production",
        }


@pytest.mark.unit
class TestSourcesDrawNoTimeoutLiteralFinding:
    @pytest.mark.parametrize("relative", _SOURCES_WITHOUT_TIMEOUT_LITERALS)
    def test_source_yields_no_literal_timeout_finding(self, relative: str) -> None:
        source = Path(model_operational_timeouts.__file__).parents[2] / relative
        assert source.is_file()
        result = ValidatorContractsAndDi().validate_file(source)
        assert [i.message for i in result.issues if i.code == "literal_timeout"] == []
