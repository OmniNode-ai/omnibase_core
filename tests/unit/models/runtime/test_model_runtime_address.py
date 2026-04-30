# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from omnibase_core.models.runtime import (
    ModelRuntimeAddress,
    ModelRuntimeAddressRegistry,
    ModelRuntimeTargetSelector,
)


def _runtime(
    runtime_id: str,
    *,
    ingress_address: str,
    capabilities: tuple[str, ...] = ("market-skills",),
    compose_project: str | None = None,
    state_root: str | None = None,
) -> ModelRuntimeAddress:
    return ModelRuntimeAddress(
        address=f"runtime://omninode-pc/{runtime_id}",
        runtime_id=runtime_id,
        box_id="omninode-pc",
        environment="dev",
        ingress_transport="unix_socket",
        ingress_address=ingress_address,
        bus_id=f"kafka-{runtime_id}",
        consumer_group_prefix=f"onex-{runtime_id}",
        capabilities=capabilities,
        compose_project=compose_project,
        state_root=state_root,
    )


def test_runtime_address_accepts_stability_lane_as_normal_address() -> None:
    address = _runtime(
        "stability-test",
        ingress_address="/tmp/onex-runtime-stability.sock",
        capabilities=("market-skills", "workflow-proof"),
        compose_project="omnibase-infra-stability-test",
        state_root="/app/data/.onex_state_stability_test",
    )

    assert address.address == "runtime://omninode-pc/stability-test"
    assert address.has_capabilities(("market-skills",))
    assert address.has_capabilities(("market-skills", "workflow-proof"))


def test_runtime_address_rejects_address_that_does_not_match_identity() -> None:
    with pytest.raises(ValidationError, match="address runtime_id must match"):
        ModelRuntimeAddress(
            address="runtime://omninode-pc/other",
            runtime_id="stability-test",
            box_id="omninode-pc",
            environment="dev",
            ingress_transport="unix_socket",
            ingress_address="/tmp/onex-runtime-stability.sock",
            bus_id="kafka-stability-test",
            consumer_group_prefix="onex-stability-test",
        )


def test_runtime_address_validates_ingress_by_transport() -> None:
    with pytest.raises(ValidationError, match="absolute path"):
        _runtime("stability-test", ingress_address="relative.sock")

    http_address = ModelRuntimeAddress(
        address="runtime://omninode-pc/http-runtime",
        runtime_id="http-runtime",
        box_id="omninode-pc",
        environment="dev",
        ingress_transport="http",
        ingress_address="http://127.0.0.1:18085/runtime",
        bus_id="kafka-http-runtime",
        consumer_group_prefix="onex-http-runtime",
    )

    assert http_address.ingress_address == "http://127.0.0.1:18085/runtime"


def test_runtime_registry_rejects_colliding_box_resources() -> None:
    production = _runtime(
        "production",
        ingress_address="/tmp/onex-runtime.sock",
        compose_project="omnibase-infra",
        state_root="/app/data/.onex_state",
    )
    duplicate_socket = _runtime(
        "stability-test",
        ingress_address="/tmp/onex-runtime.sock",
        compose_project="omnibase-infra-stability-test",
        state_root="/app/data/.onex_state_stability_test",
    )

    with pytest.raises(ValidationError, match="box-scoped ingress"):
        ModelRuntimeAddressRegistry(runtimes=(production, duplicate_socket))


def test_runtime_selector_targets_explicit_address() -> None:
    production = _runtime("production", ingress_address="/tmp/onex-runtime.sock")
    stability = _runtime(
        "stability-test",
        ingress_address="/tmp/onex-runtime-stability.sock",
        capabilities=("market-skills", "workflow-proof"),
    )
    registry = ModelRuntimeAddressRegistry(runtimes=(production, stability))

    selector = ModelRuntimeTargetSelector(
        mode="explicit",
        address="runtime://omninode-pc/stability-test",
    )

    assert selector.select_first(registry) == stability


def test_runtime_selector_filters_by_capability_and_box_preference() -> None:
    production = _runtime(
        "production",
        ingress_address="/tmp/onex-runtime.sock",
        capabilities=("market-skills",),
    )
    stability = _runtime(
        "stability-test",
        ingress_address="/tmp/onex-runtime-stability.sock",
        capabilities=("market-skills", "workflow-proof"),
    )
    registry = ModelRuntimeAddressRegistry(runtimes=(production, stability))

    selector = ModelRuntimeTargetSelector(
        mode="load_balanced",
        required_capabilities=("workflow-proof",),
        preferred_box_id="omninode-pc",
    )

    assert selector.candidates(registry) == (stability,)
