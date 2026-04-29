# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Red tests for governance model Batch C — wire schema, contract dependency, DB boundary (OMN-10247)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel


@pytest.mark.unit
class TestGovernanceBatchCWireSchema:
    """Wire schema model imports from omnibase_core.models.governance."""

    def test_model_wire_field_constraints_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_field_constraints import (
            ModelWireFieldConstraints,
        )

        assert issubclass(ModelWireFieldConstraints, BaseModel)

    def test_model_wire_required_field_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_required_field import (
            ModelWireRequiredField,
        )

        assert issubclass(ModelWireRequiredField, BaseModel)

    def test_model_wire_optional_field_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_optional_field import (
            ModelWireOptionalField,
        )

        assert issubclass(ModelWireOptionalField, BaseModel)

    def test_model_wire_renamed_field_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_renamed_field import (
            ModelWireRenamedField,
        )

        assert issubclass(ModelWireRenamedField, BaseModel)

    def test_model_wire_collapsed_field_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_collapsed_field import (
            ModelWireCollapsedField,
        )

        assert issubclass(ModelWireCollapsedField, BaseModel)

    def test_model_wire_producer_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_producer import (
            ModelWireProducer,
        )

        assert issubclass(ModelWireProducer, BaseModel)

    def test_model_wire_consumer_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_consumer import (
            ModelWireConsumer,
        )

        assert issubclass(ModelWireConsumer, BaseModel)

    def test_model_wire_ci_gate_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_ci_gate import ModelWireCiGate

        assert issubclass(ModelWireCiGate, BaseModel)

    def test_model_wire_ci_gate_rejects_unknown_fields(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.governance.model_wire_ci_gate import ModelWireCiGate

        with pytest.raises(ValidationError):
            ModelWireCiGate(
                test_file="tests/test_wire.py",
                test_class="TestWire",
                unchecked="ignored",
            )

    def test_model_wire_schema_contract_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_wire_schema_contract import (
            ModelWireSchemaContract,
        )

        assert issubclass(ModelWireSchemaContract, BaseModel)

    def test_model_wire_schema_contract_validates(self) -> None:
        from omnibase_core.enums.governance.enum_wire_field_type import (
            EnumWireFieldType,
        )
        from omnibase_core.models.governance.model_wire_consumer import (
            ModelWireConsumer,
        )
        from omnibase_core.models.governance.model_wire_producer import (
            ModelWireProducer,
        )
        from omnibase_core.models.governance.model_wire_required_field import (
            ModelWireRequiredField,
        )
        from omnibase_core.models.governance.model_wire_schema_contract import (
            ModelWireSchemaContract,
        )

        contract = ModelWireSchemaContract(
            topic="onex.evt.test.thing_happened.v1",
            schema_version="1.0.0",
            ticket="OMN-10247",
            producer=ModelWireProducer(repo="omnibase_core", file="src/handler.py"),
            consumer=ModelWireConsumer(
                repo="omnimarket", file="src/consumer.py", model="ModelThing"
            ),
            required_fields=[
                ModelWireRequiredField(name="event_id", type=EnumWireFieldType.UUID)
            ],
        )
        assert contract.topic == "onex.evt.test.thing_happened.v1"

    def test_model_wire_schema_contract_rejects_duplicate_required_fields(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.enums.governance.enum_wire_field_type import (
            EnumWireFieldType,
        )
        from omnibase_core.models.governance.model_wire_consumer import (
            ModelWireConsumer,
        )
        from omnibase_core.models.governance.model_wire_producer import (
            ModelWireProducer,
        )
        from omnibase_core.models.governance.model_wire_required_field import (
            ModelWireRequiredField,
        )
        from omnibase_core.models.governance.model_wire_schema_contract import (
            ModelWireSchemaContract,
        )

        with pytest.raises(ValidationError):
            ModelWireSchemaContract(
                topic="onex.evt.test.thing_happened.v1",
                schema_version="1.0.0",
                producer=ModelWireProducer(repo="r", file="f.py"),
                consumer=ModelWireConsumer(repo="r", file="f.py", model="M"),
                required_fields=[
                    ModelWireRequiredField(name="dup", type=EnumWireFieldType.STRING),
                    ModelWireRequiredField(name="dup", type=EnumWireFieldType.STRING),
                ],
            )

    def test_model_wire_field_constraints_rejects_contradictions(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.governance.model_wire_field_constraints import (
            ModelWireFieldConstraints,
        )

        with pytest.raises(ValidationError):
            ModelWireFieldConstraints(ge=10, le=1)

        with pytest.raises(ValidationError):
            ModelWireFieldConstraints(min_length=10, max_length=1)

    def test_model_wire_field_constraints_rejects_negative_lengths(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.governance.model_wire_field_constraints import (
            ModelWireFieldConstraints,
        )

        with pytest.raises(ValidationError):
            ModelWireFieldConstraints(min_length=-1)

        with pytest.raises(ValidationError):
            ModelWireFieldConstraints(max_length=-1)

    def test_model_wire_schema_contract_rejects_duplicate_active_renames(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.enums.governance.enum_wire_field_type import (
            EnumWireFieldType,
        )
        from omnibase_core.models.governance.model_wire_consumer import (
            ModelWireConsumer,
        )
        from omnibase_core.models.governance.model_wire_producer import (
            ModelWireProducer,
        )
        from omnibase_core.models.governance.model_wire_renamed_field import (
            ModelWireRenamedField,
        )
        from omnibase_core.models.governance.model_wire_required_field import (
            ModelWireRequiredField,
        )
        from omnibase_core.models.governance.model_wire_schema_contract import (
            ModelWireSchemaContract,
        )

        with pytest.raises(ValidationError):
            ModelWireSchemaContract(
                topic="onex.evt.test.thing_happened.v1",
                schema_version="1.0.0",
                producer=ModelWireProducer(repo="r", file="f.py"),
                consumer=ModelWireConsumer(repo="r", file="f.py", model="M"),
                required_fields=[
                    ModelWireRequiredField(name="event_id", type=EnumWireFieldType.UUID)
                ],
                renamed_fields=[
                    ModelWireRenamedField(
                        producer_name="old_id",
                        canonical_name="event_id",
                        shim_status="active",
                    ),
                    ModelWireRenamedField(
                        producer_name="old_id",
                        canonical_name="event_uuid",
                        shim_status="active",
                    ),
                ],
            )


@pytest.mark.unit
class TestGovernanceBatchCContractDependency:
    """Contract dependency models already present via batch A — verify they exist."""

    def test_model_db_table_ref_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_db_table_ref import ModelDbTableRef

        assert issubclass(ModelDbTableRef, BaseModel)

    def test_model_contract_entry_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_contract_entry import (
            ModelContractEntry,
        )

        assert issubclass(ModelContractEntry, BaseModel)

    def test_model_contract_dependency_input_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_contract_dependency_input import (
            ModelContractDependencyInput,
        )

        assert issubclass(ModelContractDependencyInput, BaseModel)

    def test_model_contract_overlap_edge_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_contract_overlap_edge import (
            ModelContractOverlapEdge,
        )

        assert issubclass(ModelContractOverlapEdge, BaseModel)

    def test_model_dependency_wave_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_dependency_wave import (
            ModelDependencyWave,
        )

        assert issubclass(ModelDependencyWave, BaseModel)

    def test_model_hotspot_topic_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_hotspot_topic import (
            ModelHotspotTopic,
        )

        assert issubclass(ModelHotspotTopic, BaseModel)

    def test_model_contract_dependency_output_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_contract_dependency_output import (
            ModelContractDependencyOutput,
        )

        assert issubclass(ModelContractDependencyOutput, BaseModel)


@pytest.mark.unit
class TestGovernanceBatchCDbBoundary:
    """DB boundary exception models."""

    def test_model_db_boundary_exception_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_db_boundary_exception import (
            ModelDbBoundaryException,
        )

        assert issubclass(ModelDbBoundaryException, BaseModel)

    def test_model_db_boundary_exceptions_registry_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_db_boundary_exceptions_registry import (
            ModelDbBoundaryExceptionsRegistry,
        )

        assert issubclass(ModelDbBoundaryExceptionsRegistry, BaseModel)

    def test_model_db_boundary_exception_validates(self) -> None:
        from omnibase_core.enums.governance.enum_db_boundary import (
            EnumDbBoundaryExceptionStatus,
            EnumDbBoundaryReasonCategory,
        )
        from omnibase_core.models.governance.model_db_boundary_exception import (
            ModelDbBoundaryException,
        )

        exc = ModelDbBoundaryException(
            repo="omnimarket",
            file="src/handler.py",
            usage="Read user table for validation",
            reason_category=EnumDbBoundaryReasonCategory.READ_MODEL,
            justification="Needed for cross-service validation",
            owner="jonah",
            approved_by="jonah",
            review_by="2026-12",
            status=EnumDbBoundaryExceptionStatus.APPROVED,
        )
        assert exc.repo == "omnimarket"

    def test_model_db_boundary_exception_rejects_bad_review_by(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.enums.governance.enum_db_boundary import (
            EnumDbBoundaryReasonCategory,
        )
        from omnibase_core.models.governance.model_db_boundary_exception import (
            ModelDbBoundaryException,
        )

        with pytest.raises(ValidationError):
            ModelDbBoundaryException(
                repo="omnimarket",
                file="src/handler.py",
                usage="x",
                reason_category=EnumDbBoundaryReasonCategory.READ_MODEL,
                justification="x",
                owner="jonah",
                approved_by="jonah",
                review_by="not-a-date",
            )

    def test_model_db_boundary_exception_rejects_unknown_fields(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.enums.governance.enum_db_boundary import (
            EnumDbBoundaryReasonCategory,
        )
        from omnibase_core.models.governance.model_db_boundary_exception import (
            ModelDbBoundaryException,
        )

        with pytest.raises(ValidationError):
            ModelDbBoundaryException(
                repo="omnimarket",
                file="src/handler.py",
                usage="x",
                reason_category=EnumDbBoundaryReasonCategory.READ_MODEL,
                justification="x",
                owner="jonah",
                approved_by="jonah",
                review_by="2026-12",
                untracked=True,
            )


@pytest.mark.unit
class TestGovernanceBatchCMigrationSpec:
    """Migration spec models."""

    def test_model_migration_spec_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_migration_spec import (
            ModelMigrationSpec,
        )

        assert issubclass(ModelMigrationSpec, BaseModel)

    def test_model_migration_validation_result_is_base_model(self) -> None:
        from omnibase_core.models.governance.model_migration_validation_result import (
            ModelMigrationValidationResult,
        )

        assert issubclass(ModelMigrationValidationResult, BaseModel)

    def test_model_migration_spec_validates(self) -> None:
        from omnibase_core.enums.governance.enum_migration_status import (
            EnumMigrationStatus,
        )
        from omnibase_core.models.governance.model_migration_spec import (
            ModelMigrationSpec,
        )

        spec = ModelMigrationSpec(
            handler_path="src/handler.py",
            node_dir="src/",
            contract_path="src/contract.yaml",
            estimated_complexity=2,
            status=EnumMigrationStatus.PENDING,
        )
        assert spec.estimated_complexity == 2

    def test_model_migration_validation_result_consistency_check(self) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.governance.model_migration_validation_result import (
            ModelMigrationValidationResult,
        )

        with pytest.raises(ValidationError):
            # passed=True but tests_failed != 0 — should raise
            ModelMigrationValidationResult(
                handler_path="src/handler.py",
                contract_dispatch_loads=True,
                test_inputs_count=3,
                tests_passed=2,
                tests_failed=1,
                passed=True,
            )

        with pytest.raises(ValidationError):
            # all checks are successful, so passed=False is inconsistent.
            ModelMigrationValidationResult(
                handler_path="src/handler.py",
                contract_dispatch_loads=True,
                test_inputs_count=3,
                tests_passed=3,
                tests_failed=0,
                passed=False,
            )
