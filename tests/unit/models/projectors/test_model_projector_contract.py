# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelProjectorContract.

Tests cover:
1. Valid contract with all required fields
2. projector_kind validates (only "materialized_view" for v1)
3. consumed_events pattern validated (lowercase.segments.vN format)
4. Unknown fields rejected (extra='forbid')
5. Frozen/immutable behavior
6. Serialization roundtrip (dict and JSON)
7. YAML roundtrip (using pyyaml if available, or skip)

Core Principle:
    "Projectors are consumers of ModelEventEnvelope streams, not participants
    in handler dispatch. They never emit events, intents, or projections."
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


@pytest.mark.unit
class TestModelProjectorContractCreation:
    """Tests for ModelProjectorContract creation and validation."""

    def test_valid_contract_minimal(self) -> None:
        """Valid contract with all required fields."""
        from omnibase_core.models.projectors import (
            ModelIdempotencyConfig,
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(
            mode="upsert",
            upsert_key="node_id",
            idempotency=ModelIdempotencyConfig(enabled=True, key="event_id"),
        )

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

        assert contract.projector_kind == "materialized_view"
        assert contract.projector_id == "node-status-projector"
        assert contract.name == "Node Status Projector"
        assert contract.version == "1.0.0"
        assert contract.aggregate_type == "node"
        assert len(contract.consumed_events) == 2
        assert "node.created.v1" in contract.consumed_events
        assert "node.updated.v1" in contract.consumed_events
        assert contract.projection_schema.table == "node_projections"
        assert contract.behavior.mode == "upsert"

    def test_valid_contract_single_event(self) -> None:
        """Valid contract with a single consumed event."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="workflow_id",
            type="UUID",
            source="event.payload.workflow_id",
        )

        schema = ModelProjectorSchema(
            table="workflow_status",
            primary_key="workflow_id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="workflow-projector",
            name="Workflow Projector",
            version="2.0.0",
            aggregate_type="workflow",
            consumed_events=["workflow.completed.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert len(contract.consumed_events) == 1
        assert contract.consumed_events[0] == "workflow.completed.v1"

    def test_valid_contract_complex_event_names(self) -> None:
        """Valid contract with complex event names containing underscores."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="order_id",
            type="UUID",
            source="event.payload.order_id",
        )

        schema = ModelProjectorSchema(
            table="orders",
            primary_key="order_id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="insert_only")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="order-projector",
            name="Order Projector",
            version="1.0.0",
            aggregate_type="order",
            consumed_events=[
                "order_management.order_created.v1",
                "order_management.order_line_item_added.v2",
                "payment.payment_received.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
        )

        assert len(contract.consumed_events) == 3
        assert "order_management.order_created.v1" in contract.consumed_events


@pytest.mark.unit
class TestModelProjectorContractProjectorKind:
    """Tests for projector_kind validation."""

    def test_materialized_view_is_valid(self) -> None:
        """projector_kind='materialized_view' is the only valid value for v1."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test_table",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert contract.projector_kind == "materialized_view"

    def test_invalid_projector_kind_rejected(self) -> None:
        """Invalid projector_kind values should be rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test_table",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="event_sourced",  # type: ignore[arg-type]
                projector_id="test-projector",
                name="Test Projector",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                behavior=behavior,
            )

        error_str = str(exc_info.value).lower()
        assert "projector_kind" in error_str or "literal" in error_str

    def test_empty_projector_kind_rejected(self) -> None:
        """Empty projector_kind should be rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test_table",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError):
            ModelProjectorContract(
                projector_kind="",  # type: ignore[arg-type]
                projector_id="test-projector",
                name="Test Projector",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                behavior=behavior,
            )


@pytest.mark.unit
class TestModelProjectorContractConsumedEvents:
    """Tests for consumed_events pattern validation."""

    def test_valid_event_pattern_simple(self) -> None:
        """Simple event names are valid: domain.action.version."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["node.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert contract.consumed_events == ["node.created.v1"]

    def test_valid_event_pattern_with_underscores(self) -> None:
        """Event names with underscores are valid."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["order_management.order_line_item_added.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert (
            contract.consumed_events[0] == "order_management.order_line_item_added.v1"
        )

    def test_valid_event_pattern_multi_segment(self) -> None:
        """Event names with multiple segments are valid."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["domain.subdomain.entity.action.v10"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert contract.consumed_events[0] == "domain.subdomain.entity.action.v10"

    def test_invalid_event_pattern_no_version(self) -> None:
        """Event names without version suffix are rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["node.created"],  # Missing version
                projection_schema=schema,
                behavior=behavior,
            )

        assert "node.created" in str(exc_info.value)

    def test_invalid_event_pattern_uppercase(self) -> None:
        """Event names with uppercase letters are rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["Node.Created.v1"],  # Uppercase not allowed
                projection_schema=schema,
                behavior=behavior,
            )

        assert "Node.Created.v1" in str(exc_info.value)

    def test_invalid_event_pattern_starts_with_number(self) -> None:
        """Event names starting with number are rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["1node.created.v1"],  # Starts with number
                projection_schema=schema,
                behavior=behavior,
            )

        assert "1node.created.v1" in str(exc_info.value)

    def test_invalid_event_pattern_hyphen(self) -> None:
        """Event names with hyphens are rejected (use underscores)."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["node-service.created.v1"],  # Hyphen not allowed
                projection_schema=schema,
                behavior=behavior,
            )

        assert "node-service.created.v1" in str(exc_info.value)

    def test_invalid_event_pattern_single_segment(self) -> None:
        """Event names with single segment are rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["v1"],  # Single segment
                projection_schema=schema,
                behavior=behavior,
            )

        assert "v1" in str(exc_info.value)

    def test_multiple_invalid_events_all_reported(self) -> None:
        """Multiple invalid event names should all be validated."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        # First invalid event should trigger error
        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=[
                    "Invalid.Event",  # Invalid: uppercase
                    "also-invalid.v1",  # Invalid: hyphen
                ],
                projection_schema=schema,
                behavior=behavior,
            )

        # At least one of the invalid events should be mentioned
        error_str = str(exc_info.value)
        assert "Invalid.Event" in error_str or "also-invalid.v1" in error_str


@pytest.mark.unit
class TestModelProjectorContractRequiredFields:
    """Tests for required field validation."""

    def test_projector_id_is_required(self) -> None:
        """projector_id field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(  # type: ignore[call-arg]
                projector_kind="materialized_view",
                # projector_id missing
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                behavior=behavior,
            )

        assert "projector_id" in str(exc_info.value)

    def test_name_is_required(self) -> None:
        """name field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(  # type: ignore[call-arg]
                projector_kind="materialized_view",
                projector_id="test-projector",
                # name missing
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                behavior=behavior,
            )

        assert "name" in str(exc_info.value)

    def test_version_is_required(self) -> None:
        """version field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(  # type: ignore[call-arg]
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                # version missing
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                behavior=behavior,
            )

        assert "version" in str(exc_info.value)

    def test_aggregate_type_is_required(self) -> None:
        """aggregate_type field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(  # type: ignore[call-arg]
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                # aggregate_type missing
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                behavior=behavior,
            )

        assert "aggregate_type" in str(exc_info.value)

    def test_consumed_events_is_required(self) -> None:
        """consumed_events field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(  # type: ignore[call-arg]
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                # consumed_events missing
                projection_schema=schema,
                behavior=behavior,
            )

        assert "consumed_events" in str(exc_info.value)

    def test_projection_schema_is_required(self) -> None:
        """projection_schema field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorContract,
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(  # type: ignore[call-arg]
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                # projection_schema missing
                behavior=behavior,
            )

        assert "projection_schema" in str(exc_info.value)

    def test_behavior_is_required(self) -> None:
        """behavior field is required."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(  # type: ignore[call-arg]
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                # behavior missing
            )

        assert "behavior" in str(exc_info.value)


@pytest.mark.unit
class TestModelProjectorContractImmutability:
    """Tests for frozen/immutable behavior."""

    def test_contract_is_frozen(self) -> None:
        """Contract should be immutable after creation."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        with pytest.raises(ValidationError):
            contract.name = "New Name"  # type: ignore[misc]

    def test_contract_projector_id_immutable(self) -> None:
        """projector_id should be immutable after creation."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        with pytest.raises(ValidationError):
            contract.projector_id = "new-id"  # type: ignore[misc]

    def test_contract_is_hashable(self) -> None:
        """Frozen contract should be hashable."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        hash_value = hash(contract)
        assert isinstance(hash_value, int)


@pytest.mark.unit
class TestModelProjectorContractExtraFields:
    """Tests for extra field rejection."""

    def test_unknown_fields_rejected(self) -> None:
        """Extra fields should be rejected."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        with pytest.raises(ValidationError) as exc_info:
            ModelProjectorContract(
                projector_kind="materialized_view",
                projector_id="test-projector",
                name="Test",
                version="1.0.0",
                aggregate_type="test",
                consumed_events=["test.created.v1"],
                projection_schema=schema,
                behavior=behavior,
                unknown_field="value",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower() or "unknown_field" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestModelProjectorContractSerialization:
    """Tests for serialization roundtrip."""

    def test_to_dict_roundtrip(self) -> None:
        """Model -> dict -> Model produces identical result."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.projectors import (
            ModelIdempotencyConfig,
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

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

        original = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-status-projector",
            name="Node Status Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.updated.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        data = original.model_dump()
        restored = ModelProjectorContract.model_validate(data)

        assert restored.projector_kind == original.projector_kind
        assert restored.projector_id == original.projector_id
        assert restored.name == original.name
        assert restored.version == original.version
        assert restored.aggregate_type == original.aggregate_type
        assert restored.consumed_events == original.consumed_events
        assert restored.projection_schema.table == original.projection_schema.table
        assert restored.behavior.mode == original.behavior.mode

    def test_to_json_roundtrip(self) -> None:
        """Model -> JSON -> Model produces identical result."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        original = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        json_str = original.model_dump_json()
        restored = ModelProjectorContract.model_validate_json(json_str)

        assert restored.projector_id == original.projector_id
        assert restored.consumed_events == original.consumed_events

    def test_to_dict_minimal_contract(self) -> None:
        """Minimal contract serialization produces expected keys."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        data = contract.model_dump()

        assert "projector_kind" in data
        assert "projector_id" in data
        assert "name" in data
        assert "version" in data
        assert "aggregate_type" in data
        assert "consumed_events" in data
        assert "projection_schema" in data
        assert "behavior" in data
        assert data["projector_kind"] == "materialized_view"
        assert data["projector_id"] == "test-projector"


@pytest.mark.unit
class TestModelProjectorContractYamlRoundtrip:
    """Tests for YAML serialization roundtrip."""

    def test_yaml_roundtrip(self) -> None:
        """Model -> YAML -> Model produces identical result (if pyyaml available)."""
        pytest.importorskip("yaml")
        import yaml

        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema = ModelProjectorSchema(
            table="node_projections",
            primary_key="node_id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert", upsert_key="node_id")

        original = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="node-projector",
            name="Node Projector",
            version="1.0.0",
            aggregate_type="node",
            consumed_events=["node.created.v1", "node.updated.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        # Serialize to YAML
        data = original.model_dump()
        yaml_str = yaml.safe_dump(data, default_flow_style=False)

        # Deserialize from YAML
        loaded_data = yaml.safe_load(yaml_str)
        restored = ModelProjectorContract.model_validate(loaded_data)

        assert restored.projector_id == original.projector_id
        assert restored.name == original.name
        assert restored.consumed_events == original.consumed_events
        assert restored.projection_schema.table == original.projection_schema.table

    def test_yaml_with_complex_events(self) -> None:
        """YAML roundtrip with complex event names."""
        pytest.importorskip("yaml")
        import yaml

        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="order_id",
            type="UUID",
            source="event.payload.order_id",
        )

        schema = ModelProjectorSchema(
            table="orders",
            primary_key="order_id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="insert_only")

        original = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="order-projector",
            name="Order Projector",
            version="2.0.0",
            aggregate_type="order",
            consumed_events=[
                "order_management.order_created.v1",
                "order_management.order_line_item_added.v2",
                "payment.payment_received.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
        )

        # Roundtrip through YAML
        yaml_str = yaml.safe_dump(original.model_dump(), default_flow_style=False)
        restored = ModelProjectorContract.model_validate(yaml.safe_load(yaml_str))

        assert len(restored.consumed_events) == 3
        assert "order_management.order_created.v1" in restored.consumed_events


@pytest.mark.unit
class TestModelProjectorContractFromAttributes:
    """Tests for from_attributes compatibility (pytest-xdist)."""

    def test_can_use_in_set(self) -> None:
        """Contract can be used in a set (hashable)."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract1 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector-1",
            name="Test 1",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        contract2 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector-2",
            name="Test 2",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        # Should be able to create a set of contracts
        contract_set = {contract1, contract2}
        assert len(contract_set) == 2

    def test_can_use_as_dict_key(self) -> None:
        """Contract can be used as dictionary key (hashable)."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        behavior = ModelProjectorBehavior(mode="upsert")

        contract = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        # Should be able to use contract as dict key
        contract_dict = {contract: "value"}
        assert contract_dict[contract] == "value"
