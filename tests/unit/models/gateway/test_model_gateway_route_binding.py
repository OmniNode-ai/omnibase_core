# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelGatewayRouteBinding — OMN-11193."""

import pytest
from pydantic import ValidationError


@pytest.mark.unit
def test_model_gateway_route_binding_create() -> None:
    from omnibase_core.models.gateway.model_gateway_route_binding import (
        ModelGatewayRouteBinding,
    )

    binding = ModelGatewayRouteBinding(
        method="POST",
        path_pattern="/api/v1/commands/run",
        contract_id="node_run_command.v1",
    )
    assert binding.method == "POST"
    assert binding.path_pattern == "/api/v1/commands/run"
    assert binding.contract_id == "node_run_command.v1"


@pytest.mark.unit
def test_model_gateway_route_binding_all_methods() -> None:
    from omnibase_core.models.gateway.model_gateway_route_binding import (
        ModelGatewayRouteBinding,
    )

    for method in ("GET", "POST", "PUT", "DELETE", "PATCH"):
        binding = ModelGatewayRouteBinding(
            method=method,  # type: ignore[arg-type]  # NOTE(OMN-11193): parametric loop over valid Literal values; Pydantic accepts the runtime strings but mypy cannot narrow.
            path_pattern="/api/v1/resource",
            contract_id="some.contract.v1",
        )
        assert binding.method == method


@pytest.mark.unit
def test_model_gateway_route_binding_invalid_method() -> None:
    from omnibase_core.models.gateway.model_gateway_route_binding import (
        ModelGatewayRouteBinding,
    )

    with pytest.raises(ValidationError):
        ModelGatewayRouteBinding(
            method="OPTIONS",  # type: ignore[arg-type]  # NOTE(OMN-11193): intentional invalid Literal value to verify ValidationError is raised.
            path_pattern="/api/v1/resource",
            contract_id="some.contract.v1",
        )


@pytest.mark.unit
def test_model_gateway_route_binding_frozen() -> None:
    from omnibase_core.models.gateway.model_gateway_route_binding import (
        ModelGatewayRouteBinding,
    )

    binding = ModelGatewayRouteBinding(
        method="GET",
        path_pattern="/api/v1/status",
        contract_id="node_status.v1",
    )
    with pytest.raises(Exception):
        binding.method = "POST"  # type: ignore[misc]  # NOTE(OMN-11193): intentional forbidden assignment to verify frozen model rejects mutation.
