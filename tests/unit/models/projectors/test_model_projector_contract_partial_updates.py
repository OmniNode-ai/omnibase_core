# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelProjectorContract partial update support.

Tests cover:
1. Contract creation with partial updates
2. Validation that partial update columns exist in schema
3. Validation that partial update trigger events are in consumed_events
4. Validation that partial update names are unique
5. Backwards compatibility (contracts without partial_updates still work)
6. Serialization roundtrip with partial updates
7. Hash and repr include partial updates

Related to OMN-1170: Partial update operations for projectors.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _create_minimal_schema() -> tuple:
    """Create a minimal schema and behavior for testing."""
    from omnibase_core.models.projectors import (
        ModelProjectorBehavior,
        ModelProjectorColumn,
        ModelProjectorSchema,
    )

    columns = [
        ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        ),
        ModelProjectorColumn(
            name="current_state",
            type="TEXT",
            source="event.payload.state",
        ),
        ModelProjectorColumn(
            name="last_heartbeat_at",
            type="TIMESTAMPTZ",
            source="event.payload.timestamp",
        ),
        ModelProjectorColumn(
            name="liveness_deadline",
            type="TIMESTAMPTZ",
            source="event.payload.deadline",
        ),
        ModelProjectorColumn(
            name="ack_timeout_emitted_at",
            type="TIMESTAMPTZ",
            source="event.payload.timeout_at",
        ),
        ModelProjectorColumn(
            name="updated_at",
            type="TIMESTAMPTZ",
            source="event.payload.updated_at",
        ),
    ]

    schema = ModelProjectorSchema(
        table="node_registrations",
        primary_key="node_id",
        columns=columns,
    )

    behavior = ModelProjectorBehavior(mode="upsert", upsert_key="node_id")

    return schema, behavior


@pytest.mark.unit
class TestModelProjectorContractWithPartialUpdates:
    """Tests for ModelProjectorContract creation with partial updates."""

    def test_contract_with_no_partial_updates(self) -> None:
        """Contract without partial updates is valid (backwards compatibility)."""
        from omnibase_core.models.projectors import ModelProjectorContract

        schema, behavior = _create_minimal_schema()

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-status-projector",
            name="Node Status Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.updated.v1"],
            projection_schema=schema,
            behavior=behavior,
            # partial_updates not specified - defaults to empty list
        )

        assert contract.partial_updates == []

    def test_contract_with_partial_updates(self) -> None:
        """Contract with partial updates is valid."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at", "liveness_deadline"],
                trigger_event="node.heartbeat.v1",
            ),
            ModelPartialUpdateOperation(
                name="state_transition",
                columns=["current_state", "updated_at"],
                trigger_event="node.state.changed.v1",
                skip_idempotency=True,
            ),
        ]

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-status-projector",
            name="Node Status Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=[
                "node.created.v1",
                "node.heartbeat.v1",
                "node.state.changed.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
            partial_updates=partial_updates,
        )

        assert len(contract.partial_updates) == 2
        assert contract.partial_updates[0].name == "heartbeat"
        assert contract.partial_updates[1].name == "state_transition"


@pytest.mark.unit
class TestPartialUpdateColumnValidation:
    """Tests for validation that partial update columns exist in schema."""

    def test_valid_partial_update_columns(self) -> None:
        """Partial update columns that exist in schema are valid."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at", "liveness_deadline"],  # Both exist
                trigger_event="node.heartbeat.v1",
            ),
        ]

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.heartbeat.v1"],
            projection_schema=schema,
            behavior=behavior,
            partial_updates=partial_updates,
        )

        assert len(contract.partial_updates) == 1

    def test_invalid_partial_update_column_not_in_schema(self) -> None:
        """Partial update column not in schema is rejected."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at", "nonexistent_column"],  # nonexistent
                trigger_event="node.heartbeat.v1",
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="node-projector",
                name="Node Projector",
                version="1.0.0",
                aggregate_type="node",
                consumed_events=["node.created.v1", "node.heartbeat.v1"],
                projection_schema=schema,
                behavior=behavior,
                partial_updates=partial_updates,
            )

        error_str = str(exc_info.value)
        assert "heartbeat" in error_str
        assert "nonexistent_column" in error_str

    def test_multiple_invalid_columns_detected(self) -> None:
        """Multiple invalid columns in partial update are detected."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="invalid_update",
                columns=["invalid1", "invalid2"],  # Both invalid
                trigger_event="node.heartbeat.v1",
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="node-projector",
                name="Node Projector",
                version="1.0.0",
                aggregate_type="node",
                consumed_events=["node.created.v1", "node.heartbeat.v1"],
                projection_schema=schema,
                behavior=behavior,
                partial_updates=partial_updates,
            )

        error_str = str(exc_info.value)
        # At least one invalid column should be mentioned
        assert "invalid1" in error_str or "invalid2" in error_str


@pytest.mark.unit
class TestPartialUpdateTriggerEventValidation:
    """Tests for validation that trigger events are in consumed_events."""

    def test_valid_trigger_event_in_consumed_events(self) -> None:
        """Trigger event that is in consumed_events is valid."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at"],
                trigger_event="node.heartbeat.v1",  # In consumed_events
            ),
        ]

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=[
                "node.created.v1",
                "node.heartbeat.v1",
            ],  # Includes heartbeat
            projection_schema=schema,
            behavior=behavior,
            partial_updates=partial_updates,
        )

        assert contract.partial_updates[0].trigger_event == "node.heartbeat.v1"

    def test_invalid_trigger_event_not_in_consumed_events(self) -> None:
        """Trigger event not in consumed_events is rejected."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at"],
                trigger_event="node.heartbeat.v1",  # NOT in consumed_events
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="node-projector",
                name="Node Projector",
                version="1.0.0",
                aggregate_type="node",
                consumed_events=["node.created.v1"],  # Missing heartbeat
                projection_schema=schema,
                behavior=behavior,
                partial_updates=partial_updates,
            )

        error_str = str(exc_info.value)
        assert "heartbeat" in error_str
        assert "node.heartbeat.v1" in error_str


@pytest.mark.unit
class TestPartialUpdateNameUniqueness:
    """Tests for validation that partial update names are unique."""

    def test_unique_partial_update_names_valid(self) -> None:
        """Unique partial update names are valid."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at"],
                trigger_event="node.heartbeat.v1",
            ),
            ModelPartialUpdateOperation(
                name="state_transition",
                columns=["current_state"],
                trigger_event="node.state.changed.v1",
            ),
        ]

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=[
                "node.created.v1",
                "node.heartbeat.v1",
                "node.state.changed.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
            partial_updates=partial_updates,
        )

        assert len(contract.partial_updates) == 2

    def test_duplicate_partial_update_names_rejected(self) -> None:
        """Duplicate partial update names are rejected."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",  # Duplicate name
                columns=["last_heartbeat_at"],
                trigger_event="node.heartbeat.v1",
            ),
            ModelPartialUpdateOperation(
                name="heartbeat",  # Duplicate name
                columns=["liveness_deadline"],
                trigger_event="node.heartbeat.v1",
            ),
        ]

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="node-projector",
                name="Node Projector",
                version="1.0.0",
                aggregate_type="node",
                consumed_events=["node.created.v1", "node.heartbeat.v1"],
                projection_schema=schema,
                behavior=behavior,
                partial_updates=partial_updates,
            )

        error_str = str(exc_info.value)
        assert "heartbeat" in error_str
        assert "duplicate" in error_str.lower()


@pytest.mark.unit
class TestPartialUpdateSerializationRoundtrip:
    """Tests for serialization roundtrip with partial updates."""

    def test_to_dict_roundtrip_with_partial_updates(self) -> None:
        """Model -> dict -> Model produces identical result with partial updates."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at", "liveness_deadline"],
                trigger_event="node.heartbeat.v1",
            ),
            ModelPartialUpdateOperation(
                name="ack_timeout",
                columns=["ack_timeout_emitted_at"],
                trigger_event="node.ack.timeout.v1",
                condition="ack_timeout_emitted_at IS NULL",
            ),
        ]

        original = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=[
                "node.created.v1",
                "node.heartbeat.v1",
                "node.ack.timeout.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
            partial_updates=partial_updates,
        )

        data = original.model_dump()
        restored = ModelProjectorContract.model_validate(data)

        assert len(restored.partial_updates) == 2
        assert restored.partial_updates[0].name == "heartbeat"
        assert restored.partial_updates[0].columns == [
            "last_heartbeat_at",
            "liveness_deadline",
        ]
        assert restored.partial_updates[1].name == "ack_timeout"
        assert restored.partial_updates[1].condition == "ack_timeout_emitted_at IS NULL"

    def test_yaml_roundtrip_with_partial_updates(self) -> None:
        """Model -> YAML -> Model produces identical result with partial updates."""
        pytest.importorskip("yaml")
        import yaml

        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="state_transition",
                columns=["current_state", "updated_at"],
                trigger_event="node.state.changed.v1",
                skip_idempotency=True,
            ),
        ]

        original = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.state.changed.v1"],
            projection_schema=schema,
            behavior=behavior,
            partial_updates=partial_updates,
        )

        yaml_str = yaml.safe_dump(original.model_dump(), default_flow_style=False)
        loaded_data = yaml.safe_load(yaml_str)
        restored = ModelProjectorContract.model_validate(loaded_data)

        assert len(restored.partial_updates) == 1
        assert restored.partial_updates[0].name == "state_transition"
        assert restored.partial_updates[0].skip_idempotency is True


@pytest.mark.unit
class TestPartialUpdateReprAndHash:
    """Tests for __repr__ and __hash__ including partial updates."""

    def test_repr_includes_partial_updates_count(self) -> None:
        """Contract repr includes partial_updates count."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        partial_updates = [
            ModelPartialUpdateOperation(
                name="heartbeat",
                columns=["last_heartbeat_at"],
                trigger_event="node.heartbeat.v1",
            ),
            ModelPartialUpdateOperation(
                name="state",
                columns=["current_state"],
                trigger_event="node.state.changed.v1",
            ),
        ]

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=[
                "node.created.v1",
                "node.heartbeat.v1",
                "node.state.changed.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
            partial_updates=partial_updates,
        )

        result = repr(contract)
        assert "partial_updates=2" in result

    def test_repr_shows_zero_partial_updates(self) -> None:
        """Contract repr shows partial_updates=0 when none specified."""
        from omnibase_core.models.projectors import ModelProjectorContract

        schema, behavior = _create_minimal_schema()

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        result = repr(contract)
        assert "partial_updates=0" in result

    def test_hash_differs_with_partial_updates(self) -> None:
        """Contract hash differs when partial updates are different."""
        from omnibase_core.models.projectors import (
            ModelPartialUpdateOperation,
            ModelProjectorContract,
        )

        schema, behavior = _create_minimal_schema()

        contract_without = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.heartbeat.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        contract_with = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.heartbeat.v1"],
            projection_schema=schema,
            behavior=behavior,
            partial_updates=[
                ModelPartialUpdateOperation(
                    name="heartbeat",
                    columns=["last_heartbeat_at"],
                    trigger_event="node.heartbeat.v1",
                ),
            ],
        )

        assert hash(contract_without) != hash(contract_with)


@pytest.mark.unit
class TestPartialUpdateBackwardsCompatibility:
    """Tests for backwards compatibility with existing contracts."""

    def test_existing_contract_without_partial_updates_still_works(self) -> None:
        """Existing contracts without partial_updates field still validate."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.projectors import (
            ModelIdempotencyConfig,
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        # Create a contract exactly as in existing tests (no partial_updates)
        columns = [
            ModelProjectorColumn(
                name="node_id",
                type="UUID",
                source="event.payload.node_id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
                on_event="node.status.changed.v1",
                default="PENDING",
            ),
        ]

        indexes = [
            ModelProjectorIndex(columns=["status"]),
        ]

        version = ModelSemVer(major=1, minor=2, patch=3)

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=columns,
            indexes=indexes,
            version=version,
        )

        idempotency = ModelIdempotencyConfig(enabled=True, key="event_id")
        behavior = ModelProjectorBehavior(
            mode="upsert",
            upsert_key="node_id",
            idempotency=idempotency,
        )

        # This should work without specifying partial_updates
        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-status-projector",
            name="Node Status Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.updated.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert contract.partial_updates == []
        assert contract.projector_id == "node-status-projector"

    def test_existing_dict_without_partial_updates_validates(self) -> None:
        """Existing dict data without partial_updates field validates."""
        from omnibase_core.models.projectors import ModelProjectorContract

        # Simulate data from an existing YAML contract without partial_updates
        data = {
            "projector_kind": "materialized_view",
            "projector_id": "legacy-projector",
            "name": "Legacy Projector",
            "version": "1.0.0",
            "aggregate_type": "legacy",
            "consumed_events": ["legacy.created.v1"],
            "projection_schema": {
                "table": "legacy_table",
                "primary_key": "id",
                "columns": [
                    {"name": "id", "type": "UUID", "source": "event.payload.id"},
                ],
            },
            "behavior": {"mode": "upsert", "upsert_key": "id"},
            # partial_updates not present - backwards compatibility
        }

        contract = ModelProjectorContract.model_validate(data)

        assert contract.partial_updates == []
        assert contract.projector_id == "legacy-projector"
