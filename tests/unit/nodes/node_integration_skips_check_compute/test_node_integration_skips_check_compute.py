# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Direct typed-record matching parity for each guard rule."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.nodes.integration_skips_check.model_integration_skip_record import (
    ModelIntegrationSkipRecord,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skip_service_config import (
    ModelIntegrationSkipServiceConfig,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_check_config import (
    ModelIntegrationSkipsCheckConfig,
)
from omnibase_core.models.nodes.integration_skips_check.model_integration_skips_check_input import (
    ModelIntegrationSkipsCheckInput,
)
from omnibase_core.nodes.node_integration_skips_check_compute.handler import (
    NodeIntegrationSkipsCheckCompute,
)

pytestmark = pytest.mark.unit


def test_parity_required_service_takes_precedence_over_optional() -> None:
    config = ModelIntegrationSkipsCheckConfig(
        required_services={
            "first": ModelIntegrationSkipServiceConfig(
                missing_skip_patterns=("postgres",)
            ),
            "second": ModelIntegrationSkipServiceConfig(
                missing_skip_patterns=("postgres",)
            ),
        },
        allowed_optional_skip_patterns=("postgres",),
    )
    request = ModelIntegrationSkipsCheckInput(
        executed=1,
        total_cases=2,
        config=config,
        strict=True,
        skipped=(
            ModelIntegrationSkipRecord(
                path="report.xml", line=4, test_name="t::db", reason="POSTGRES absent"
            ),
        ),
    )
    report = NodeIntegrationSkipsCheckCompute().handle(request)
    assert report.overall_status == "FAIL"
    assert len(report.findings) == 1
    assert report.findings[0].rule_id == "false-green"
    assert report.findings[0].location == "report.xml:4"
    assert "service 'first'" in report.findings[0].message
    assert "job provisions first" in report.findings[0].message


@pytest.mark.parametrize(
    ("strict", "optional", "expected"),
    [(False, False, "PASS"), (True, False, "FAIL"), (True, True, "PASS")],
)
def test_parity_strict_and_optional(
    strict: bool, optional: bool, expected: str
) -> None:
    config = ModelIntegrationSkipsCheckConfig(
        allowed_optional_skip_patterns=("feature",) if optional else ()
    )
    report = NodeIntegrationSkipsCheckCompute().handle(
        ModelIntegrationSkipsCheckInput(
            executed=1,
            total_cases=2,
            config=config,
            strict=strict,
            skipped=(
                ModelIntegrationSkipRecord(
                    path="r.xml", line=2, test_name="opt", reason="feature"
                ),
            ),
        )
    )
    assert report.overall_status == expected
    if report.findings:
        assert report.findings[0].rule_id == "unclassified-skip"


@pytest.mark.parametrize(
    ("executed", "minimum", "disabled", "expected"),
    [
        (0, 1, False, "FAIL"),
        (1, 1, False, "PASS"),
        (1, 2, False, "FAIL"),
        (0, 1, True, "PASS"),
        (0, -1, False, "PASS"),
    ],
)
def test_parity_collection_threshold_and_opt_out(
    executed: int, minimum: int, disabled: bool, expected: str
) -> None:
    report = NodeIntegrationSkipsCheckCompute().handle(
        ModelIntegrationSkipsCheckInput(
            executed=executed,
            total_cases=executed,
            config=ModelIntegrationSkipsCheckConfig(
                require_executed_min=minimum, silent_skip_allowed=disabled
            ),
        )
    )
    assert report.overall_status == expected
    if report.findings:
        assert report.findings[0].rule_id == "under-collection"
        assert report.findings[0].location == "<reports>:1"


def test_parity_models_are_frozen_and_forbid_extra() -> None:
    config = ModelIntegrationSkipsCheckConfig()
    with pytest.raises(ValidationError):
        config.require_executed_min = 2
    with pytest.raises(ValidationError):
        ModelIntegrationSkipsCheckConfig.model_validate({"surprise": True})
