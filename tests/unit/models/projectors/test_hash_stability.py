# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for hash stability of projector models.

These tests verify that custom __hash__ implementations:
1. Produce stable hashes across multiple calls
2. Produce different hashes for different data
3. Work correctly with set() and dict() operations
4. Produce identical hashes for reconstructed/copied objects
5. Maintain hash consistency after serialization roundtrips

Models tested:
- ModelProjectorContract
- ModelProjectorSchema
- ModelProjectorIndex

These models have custom __hash__ implementations to support hashing with
list fields by converting them to tuples.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestModelProjectorIndexHashStability:
    """Tests for ModelProjectorIndex hash stability."""

    def test_hash_stability_identical_indexes(self) -> None:
        """Same data produces same hash across calls."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(columns=["status", "created_at"], unique=True)
        index2 = ModelProjectorIndex(columns=["status", "created_at"], unique=True)

        assert hash(index1) == hash(index2)
        assert index1 == index2

    def test_hash_stability_repeated_calls(self) -> None:
        """Hash is stable across multiple calls on same object."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(columns=["status"])

        hash1 = hash(index)
        hash2 = hash(index)
        hash3 = hash(index)

        assert hash1 == hash2 == hash3

    def test_hash_differs_for_different_columns(self) -> None:
        """Different columns produce different hashes."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(columns=["status"])
        index2 = ModelProjectorIndex(columns=["created_at"])

        assert hash(index1) != hash(index2)

    def test_hash_differs_for_different_column_order(self) -> None:
        """Different column order produces different hashes."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(columns=["status", "created_at"])
        index2 = ModelProjectorIndex(columns=["created_at", "status"])

        assert hash(index1) != hash(index2)

    def test_hash_differs_for_unique_flag(self) -> None:
        """Different unique flag produces different hashes."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(columns=["status"], unique=True)
        index2 = ModelProjectorIndex(columns=["status"], unique=False)

        assert hash(index1) != hash(index2)

    def test_hash_differs_for_index_type(self) -> None:
        """Different index type produces different hashes."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(columns=["status"], type="btree")
        index2 = ModelProjectorIndex(columns=["status"], type="hash")

        assert hash(index1) != hash(index2)

    def test_hash_differs_for_name(self) -> None:
        """Different name produces different hashes."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(columns=["status"], name="idx_status")
        index2 = ModelProjectorIndex(columns=["status"], name="idx_other")

        assert hash(index1) != hash(index2)

    def test_set_deduplication_works(self) -> None:
        """Identical indexes are deduplicated in sets."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(columns=["status", "created_at"])
        index2 = ModelProjectorIndex(columns=["status", "created_at"])

        index_set = {index1, index2}
        assert len(index_set) == 1

    def test_dict_key_lookup_works(self) -> None:
        """Index can be used as dict key with proper lookup."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index = ModelProjectorIndex(columns=["status"])
        lookup_index = ModelProjectorIndex(columns=["status"])

        index_dict = {index: "value"}
        assert index_dict[lookup_index] == "value"

    def test_hash_after_serialization_roundtrip(self) -> None:
        """Hash is preserved after dict serialization roundtrip."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        original = ModelProjectorIndex(
            name="idx_composite",
            columns=["status", "created_at"],
            type="btree",
            unique=True,
        )

        data = original.model_dump()
        restored = ModelProjectorIndex.model_validate(data)

        assert hash(original) == hash(restored)
        assert original == restored


@pytest.mark.unit
class TestModelProjectorSchemaHashStability:
    """Tests for ModelProjectorSchema hash stability."""

    def test_hash_stability_identical_schemas(self) -> None:
        """Same data produces same hash across calls."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="node_id",
            type="UUID",
            source="event.payload.node_id",
        )

        schema1 = ModelProjectorSchema(
            table="nodes",
            primary_key="node_id",
            columns=[column],
        )

        schema2 = ModelProjectorSchema(
            table="nodes",
            primary_key="node_id",
            columns=[column],
        )

        assert hash(schema1) == hash(schema2)
        assert schema1 == schema2

    def test_hash_stability_repeated_calls(self) -> None:
        """Hash is stable across multiple calls on same object."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
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

        hash1 = hash(schema)
        hash2 = hash(schema)
        hash3 = hash(schema)

        assert hash1 == hash2 == hash3

    def test_hash_differs_for_different_table(self) -> None:
        """Different table name produces different hashes."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema1 = ModelProjectorSchema(
            table="table_a",
            primary_key="id",
            columns=[column],
        )

        schema2 = ModelProjectorSchema(
            table="table_b",
            primary_key="id",
            columns=[column],
        )

        assert hash(schema1) != hash(schema2)

    def test_hash_differs_for_different_primary_key(self) -> None:
        """Different primary key produces different hashes."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        col_a = ModelProjectorColumn(
            name="col_a",
            type="UUID",
            source="event.payload.col_a",
        )

        col_b = ModelProjectorColumn(
            name="col_b",
            type="UUID",
            source="event.payload.col_b",
        )

        schema1 = ModelProjectorSchema(
            table="test",
            primary_key="col_a",
            columns=[col_a, col_b],
        )

        schema2 = ModelProjectorSchema(
            table="test",
            primary_key="col_b",
            columns=[col_a, col_b],
        )

        assert hash(schema1) != hash(schema2)

    def test_hash_differs_for_different_columns(self) -> None:
        """Different columns produce different hashes."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        col_a = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        col_b = ModelProjectorColumn(
            name="id",
            type="TEXT",  # Different type
            source="event.payload.id",
        )

        schema1 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[col_a],
        )

        schema2 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[col_b],
        )

        assert hash(schema1) != hash(schema2)

    def test_hash_differs_for_different_indexes(self) -> None:
        """Different indexes produce different hashes."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema1 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
            indexes=[ModelProjectorIndex(columns=["id"])],
        )

        schema2 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
            indexes=[],  # No indexes
        )

        assert hash(schema1) != hash(schema2)

    def test_hash_differs_for_different_version(self) -> None:
        """Different version produces different hashes."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema1 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
            version=ModelSemVer(major=1, minor=0, patch=0),
        )

        schema2 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
            version=ModelSemVer(major=2, minor=0, patch=0),
        )

        assert hash(schema1) != hash(schema2)

    def test_set_deduplication_works(self) -> None:
        """Identical schemas are deduplicated in sets."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema1 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        schema2 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        schema_set = {schema1, schema2}
        assert len(schema_set) == 1

    def test_dict_key_lookup_works(self) -> None:
        """Schema can be used as dict key with proper lookup."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
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

        lookup_schema = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        schema_dict = {schema: "value"}
        assert schema_dict[lookup_schema] == "value"

    def test_hash_after_serialization_roundtrip(self) -> None:
        """Hash is preserved after dict serialization roundtrip."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="id",
                type="UUID",
                source="event.payload.id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
            ),
        ]

        original = ModelProjectorSchema(
            table="complex_table",
            primary_key="id",
            columns=columns,
            indexes=[ModelProjectorIndex(columns=["status"])],
            version=ModelSemVer(major=1, minor=2, patch=3),
        )

        data = original.model_dump()
        restored = ModelProjectorSchema.model_validate(data)

        assert hash(original) == hash(restored)
        assert original == restored


@pytest.mark.unit
class TestModelProjectorContractHashStability:
    """Tests for ModelProjectorContract hash stability."""

    def _create_minimal_contract(
        self,
        projector_id: str = "test-projector",
        name: str = "Test Projector",
        version: str = "1.0.0",
        consumed_events: list[str] | None = None,
    ) -> ModelProjectorContract:
        """Helper to create a minimal contract for testing."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorSchema,
        )

        if consumed_events is None:
            consumed_events = ["test.created.v1"]

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

        behavior = ModelProjectorBehavior(mode="upsert", upsert_key="id")

        return ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id=projector_id,
            name=name,
            version=version,
            aggregate_type="test",
            consumed_events=consumed_events,
            projection_schema=schema,
            behavior=behavior,
        )

    def test_hash_stability_identical_contracts(self) -> None:
        """Same data produces same hash across calls."""
        contract1 = self._create_minimal_contract()
        contract2 = self._create_minimal_contract()

        assert hash(contract1) == hash(contract2)
        assert contract1 == contract2

    def test_hash_stability_repeated_calls(self) -> None:
        """Hash is stable across multiple calls on same object."""
        contract = self._create_minimal_contract()

        hash1 = hash(contract)
        hash2 = hash(contract)
        hash3 = hash(contract)

        assert hash1 == hash2 == hash3

    def test_hash_differs_for_different_projector_id(self) -> None:
        """Different projector_id produces different hashes."""
        contract1 = self._create_minimal_contract(projector_id="proj-1")
        contract2 = self._create_minimal_contract(projector_id="proj-2")

        assert hash(contract1) != hash(contract2)

    def test_hash_differs_for_different_name(self) -> None:
        """Different name produces different hashes."""
        contract1 = self._create_minimal_contract(name="Projector A")
        contract2 = self._create_minimal_contract(name="Projector B")

        assert hash(contract1) != hash(contract2)

    def test_hash_differs_for_different_version(self) -> None:
        """Different version produces different hashes."""
        contract1 = self._create_minimal_contract(version="1.0.0")
        contract2 = self._create_minimal_contract(version="2.0.0")

        assert hash(contract1) != hash(contract2)

    def test_hash_differs_for_different_consumed_events(self) -> None:
        """Different consumed_events produce different hashes."""
        contract1 = self._create_minimal_contract(
            consumed_events=["event.one.v1"],
        )
        contract2 = self._create_minimal_contract(
            consumed_events=["event.two.v1"],
        )

        assert hash(contract1) != hash(contract2)

    def test_hash_differs_for_different_event_order(self) -> None:
        """Different event order produces different hashes."""
        contract1 = self._create_minimal_contract(
            consumed_events=["event.first.v1", "event.second.v1"],
        )
        contract2 = self._create_minimal_contract(
            consumed_events=["event.second.v1", "event.first.v1"],
        )

        assert hash(contract1) != hash(contract2)

    def test_hash_differs_for_different_event_count(self) -> None:
        """Different number of events produces different hashes."""
        contract1 = self._create_minimal_contract(
            consumed_events=["event.one.v1"],
        )
        contract2 = self._create_minimal_contract(
            consumed_events=["event.one.v1", "event.two.v1"],
        )

        assert hash(contract1) != hash(contract2)

    def test_set_deduplication_works(self) -> None:
        """Identical contracts are deduplicated in sets."""
        contract1 = self._create_minimal_contract()
        contract2 = self._create_minimal_contract()

        contract_set = {contract1, contract2}
        assert len(contract_set) == 1

    def test_set_contains_different_contracts(self) -> None:
        """Different contracts are not deduplicated in sets."""
        contract1 = self._create_minimal_contract(projector_id="proj-1")
        contract2 = self._create_minimal_contract(projector_id="proj-2")
        contract3 = self._create_minimal_contract(projector_id="proj-3")

        contract_set = {contract1, contract2, contract3}
        assert len(contract_set) == 3

    def test_dict_key_lookup_works(self) -> None:
        """Contract can be used as dict key with proper lookup."""
        contract = self._create_minimal_contract()
        lookup_contract = self._create_minimal_contract()

        contract_dict = {contract: "value"}
        assert contract_dict[lookup_contract] == "value"

    def test_dict_key_lookup_different_contracts(self) -> None:
        """Different contracts have independent dict entries."""
        contract1 = self._create_minimal_contract(projector_id="proj-1")
        contract2 = self._create_minimal_contract(projector_id="proj-2")

        contract_dict = {contract1: "value1", contract2: "value2"}

        assert len(contract_dict) == 2
        assert contract_dict[contract1] == "value1"
        assert contract_dict[contract2] == "value2"

    def test_hash_after_serialization_roundtrip(self) -> None:
        """Hash is preserved after dict serialization roundtrip."""
        from omnibase_core.models.projectors import ModelProjectorContract

        original = self._create_minimal_contract(
            projector_id="roundtrip-projector",
            name="Roundtrip Test Projector",
            version="3.2.1",
            consumed_events=["test.created.v1", "test.updated.v1"],
        )

        data = original.model_dump()
        restored = ModelProjectorContract.model_validate(data)

        assert hash(original) == hash(restored)
        assert original == restored

    def test_hash_after_json_roundtrip(self) -> None:
        """Hash is preserved after JSON serialization roundtrip."""
        from omnibase_core.models.projectors import ModelProjectorContract

        original = self._create_minimal_contract()

        json_str = original.model_dump_json()
        restored = ModelProjectorContract.model_validate_json(json_str)

        assert hash(original) == hash(restored)
        assert original == restored


@pytest.mark.unit
class TestModelProjectorContractHashWithComplexData:
    """Tests for contract hash with complex nested data."""

    def test_hash_with_multiple_columns_and_indexes(self) -> None:
        """Hash works correctly with complex schema."""
        from omnibase_core.models.projectors import (
            ModelProjectorBehavior,
            ModelProjectorColumn,
            ModelProjectorContract,
            ModelProjectorIndex,
            ModelProjectorSchema,
        )

        columns = [
            ModelProjectorColumn(
                name="order_id",
                type="UUID",
                source="event.payload.order_id",
            ),
            ModelProjectorColumn(
                name="customer_id",
                type="UUID",
                source="event.payload.customer_id",
            ),
            ModelProjectorColumn(
                name="status",
                type="TEXT",
                source="event.payload.status",
                default="PENDING",
            ),
            ModelProjectorColumn(
                name="created_at",
                type="TIMESTAMP",
                source="event.metadata.timestamp",
            ),
        ]

        indexes = [
            ModelProjectorIndex(columns=["customer_id"]),
            ModelProjectorIndex(columns=["status"]),
            ModelProjectorIndex(
                columns=["customer_id", "status"],
                unique=True,
                name="idx_customer_status",
            ),
        ]

        schema = ModelProjectorSchema(
            table="orders",
            primary_key="order_id",
            columns=columns,
            indexes=indexes,
        )

        behavior = ModelProjectorBehavior(mode="upsert", upsert_key="order_id")

        contract1 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="order-projector",
            name="Order Projector",
            version="1.0.0",
            aggregate_type="order",
            consumed_events=[
                "order.created.v1",
                "order.updated.v1",
                "order.cancelled.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
        )

        # Create identical contract
        contract2 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="order-projector",
            name="Order Projector",
            version="1.0.0",
            aggregate_type="order",
            consumed_events=[
                "order.created.v1",
                "order.updated.v1",
                "order.cancelled.v1",
            ],
            projection_schema=schema,
            behavior=behavior,
        )

        assert hash(contract1) == hash(contract2)
        assert contract1 == contract2
        assert {contract1, contract2} == {contract1}

    def test_hash_with_idempotency_config(self) -> None:
        """Hash works correctly with idempotency configuration."""
        from omnibase_core.models.projectors import (
            ModelIdempotencyConfig,
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

        idempotency = ModelIdempotencyConfig(enabled=True, key="event_id")
        behavior = ModelProjectorBehavior(
            mode="upsert",
            upsert_key="id",
            idempotency=idempotency,
        )

        contract1 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="idempotent-projector",
            name="Idempotent Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        contract2 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="idempotent-projector",
            name="Idempotent Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert hash(contract1) == hash(contract2)
        assert contract1 == contract2

    def test_hash_differs_with_different_behavior_mode(self) -> None:
        """Different behavior mode produces different hashes."""
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

        behavior_upsert = ModelProjectorBehavior(mode="upsert", upsert_key="id")
        behavior_insert = ModelProjectorBehavior(mode="insert_only")

        contract1 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior_upsert,
        )

        contract2 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior_insert,
        )

        assert hash(contract1) != hash(contract2)

    def test_hash_stability_with_schema_version(self) -> None:
        """Hash is stable with schema version."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer
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
            version=ModelSemVer(major=2, minor=1, patch=0),
        )

        behavior = ModelProjectorBehavior(mode="upsert", upsert_key="id")

        contract1 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="versioned-projector",
            name="Versioned Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        contract2 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="versioned-projector",
            name="Versioned Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        assert hash(contract1) == hash(contract2)
        assert contract1 == contract2


@pytest.mark.unit
class TestHashEquivalenceWithEquality:
    """Tests verifying hash/equality contract: equal objects must have equal hashes."""

    def test_index_hash_equals_implies_hash_equal(self) -> None:
        """Equal indexes must have equal hashes."""
        from omnibase_core.models.projectors import ModelProjectorIndex

        index1 = ModelProjectorIndex(
            name="idx_test",
            columns=["a", "b", "c"],
            type="btree",
            unique=True,
        )
        index2 = ModelProjectorIndex(
            name="idx_test",
            columns=["a", "b", "c"],
            type="btree",
            unique=True,
        )

        if index1 == index2:
            assert hash(index1) == hash(index2)

    def test_schema_equals_implies_hash_equal(self) -> None:
        """Equal schemas must have equal hashes."""
        from omnibase_core.models.projectors import (
            ModelProjectorColumn,
            ModelProjectorSchema,
        )

        column = ModelProjectorColumn(
            name="id",
            type="UUID",
            source="event.payload.id",
        )

        schema1 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )
        schema2 = ModelProjectorSchema(
            table="test",
            primary_key="id",
            columns=[column],
        )

        if schema1 == schema2:
            assert hash(schema1) == hash(schema2)

    def test_contract_equals_implies_hash_equal(self) -> None:
        """Equal contracts must have equal hashes."""
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

        behavior = ModelProjectorBehavior(mode="upsert", upsert_key="id")

        contract1 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        contract2 = ModelProjectorContract(
            projector_kind="materialized_view",
            projector_id="test-projector",
            name="Test Projector",
            version="1.0.0",
            aggregate_type="test",
            consumed_events=["test.created.v1"],
            projection_schema=schema,
            behavior=behavior,
        )

        if contract1 == contract2:
            assert hash(contract1) == hash(contract2)
