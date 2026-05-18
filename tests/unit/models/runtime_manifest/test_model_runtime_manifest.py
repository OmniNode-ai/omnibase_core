# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

import pytest

from omnibase_core.models.runtime_manifest import (
    ModelManifestContract,
    ModelManifestHandler,
    ModelOwnershipViolation,
    ModelRuntimeManifest,
)


def _make_contract(name: str, contract_hash: str) -> ModelManifestContract:
    return ModelManifestContract(
        name=name,
        version="1.0.0",
        node_type="COMPUTE",
        contract_hash=contract_hash,
    )


def _make_handler(name: str) -> ModelManifestHandler:
    return ModelManifestHandler(
        name=name,
        module_path=f"omnibase_core.handlers.{name}",
        routing_strategy="default",
    )


def _base_manifest(**kwargs: object) -> ModelRuntimeManifest:
    defaults: dict[str, object] = {
        "runtime_profile": "test",
        "started_at": datetime(2025, 1, 1, tzinfo=UTC),
    }
    defaults.update(kwargs)
    return ModelRuntimeManifest(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestModelRuntimeManifest:
    def test_create_manifest_with_ownership(self) -> None:
        contract = _make_contract("node.compute.v1", "abc123")
        handler = _make_handler("handle_compute")
        violation = ModelOwnershipViolation(
            contract_name="node.compute.v1",
            violation_type="duplicate_ownership",
            detail="Already claimed by node-b",
        )
        manifest = _base_manifest(
            contracts=(contract,),
            owned_command_topics=frozenset({"onex.cmd.compute.run.v1"}),
            subscribed_event_topics=frozenset({"onex.evt.compute.done.v1"}),
            handlers=(handler,),
            ownership_violations=(violation,),
        )

        assert manifest.runtime_profile == "test"
        assert len(manifest.contracts) == 1
        assert len(manifest.ownership_violations) == 1
        assert manifest.ownership_violations[0].violation_type == "duplicate_ownership"
        assert "onex.cmd.compute.run.v1" in manifest.owned_command_topics

    def test_contract_hash_deterministic_regardless_of_order(self) -> None:
        c1 = _make_contract("node.a.v1", "hash-aaa")
        c2 = _make_contract("node.b.v1", "hash-bbb")

        manifest_ab = _base_manifest(contracts=(c1, c2))
        manifest_ba = _base_manifest(contracts=(c2, c1))

        assert manifest_ab.contract_hash == manifest_ba.contract_hash

    def test_topology_hash_covers_profile_topics_handlers(self) -> None:
        handler = _make_handler("handle_x")
        manifest_a = _base_manifest(
            runtime_profile="profile-a",
            handlers=(handler,),
            owned_command_topics=frozenset({"onex.cmd.x.v1"}),
        )
        manifest_b = _base_manifest(
            runtime_profile="profile-b",
            handlers=(handler,),
            owned_command_topics=frozenset({"onex.cmd.x.v1"}),
        )

        assert manifest_a.topology_hash != manifest_b.topology_hash

    def test_frozen(self) -> None:
        manifest = _base_manifest()
        with pytest.raises(Exception):
            manifest.runtime_profile = "mutated"  # type: ignore[misc]
