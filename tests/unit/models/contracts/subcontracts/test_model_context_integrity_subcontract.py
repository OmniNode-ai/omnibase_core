# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelContextIntegritySubcontract and helper models."""

import pytest

from omnibase_core.enums.enum_retrieval_source_type import EnumRetrievalSourceType
from omnibase_core.models.contracts.subcontracts.model_context_integrity_subcontract import (
    ModelContextIntegritySubcontract,
)
from omnibase_core.models.contracts.subcontracts.model_retrieval_source import (
    ModelRetrievalSource,
)
from omnibase_core.models.contracts.subcontracts.model_return_schema import (
    ModelReturnSchema,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestEnumRetrievalSourceType:
    """Tests for EnumRetrievalSourceType enum."""

    def test_vector_value(self) -> None:
        assert EnumRetrievalSourceType.VECTOR.value == "vector"

    def test_structured_value(self) -> None:
        assert EnumRetrievalSourceType.STRUCTURED.value == "structured"

    def test_file_value(self) -> None:
        assert EnumRetrievalSourceType.FILE.value == "file"

    def test_all_values_present(self) -> None:
        values = {e.value for e in EnumRetrievalSourceType}
        assert values == {"vector", "structured", "file"}


@pytest.mark.unit
class TestModelRetrievalSource:
    """Tests for ModelRetrievalSource model."""

    def test_minimal_construction(self) -> None:
        source = ModelRetrievalSource(
            source_type=EnumRetrievalSourceType.VECTOR,
            namespace="embeddings",
        )
        assert source.source_type == EnumRetrievalSourceType.VECTOR
        assert source.namespace == "embeddings"
        assert source.keys == []
        assert source.k == 5

    def test_full_construction(self) -> None:
        source = ModelRetrievalSource(
            source_type=EnumRetrievalSourceType.STRUCTURED,
            namespace="postgres.audit_events",
            keys=["ticket_id", "session_id"],
            k=10,
        )
        assert source.source_type == EnumRetrievalSourceType.STRUCTURED
        assert source.namespace == "postgres.audit_events"
        assert source.keys == ["ticket_id", "session_id"]
        assert source.k == 10

    def test_frozen_immutability(self) -> None:
        source = ModelRetrievalSource(
            source_type=EnumRetrievalSourceType.FILE,
            namespace="docs",
        )
        with pytest.raises(Exception):
            source.namespace = "other"  # type: ignore[misc]

    def test_k_minimum_validation(self) -> None:
        with pytest.raises(Exception):
            ModelRetrievalSource(
                source_type=EnumRetrievalSourceType.VECTOR,
                namespace="test",
                k=0,
            )

    def test_k_maximum_validation(self) -> None:
        with pytest.raises(Exception):
            ModelRetrievalSource(
                source_type=EnumRetrievalSourceType.VECTOR,
                namespace="test",
                k=101,
            )


@pytest.mark.unit
class TestModelReturnSchema:
    """Tests for ModelReturnSchema model."""

    def test_minimal_construction(self) -> None:
        schema = ModelReturnSchema()
        assert schema.allowed_fields == []
        assert schema.max_tokens is None

    def test_full_construction(self) -> None:
        schema = ModelReturnSchema(
            allowed_fields=["status", "pr_url", "branch"],
            max_tokens=500,
        )
        assert schema.allowed_fields == ["status", "pr_url", "branch"]
        assert schema.max_tokens == 500

    def test_frozen_immutability(self) -> None:
        schema = ModelReturnSchema(allowed_fields=["status"])
        with pytest.raises(Exception):
            schema.max_tokens = 100  # type: ignore[misc]


@pytest.mark.unit
class TestModelContextIntegritySubcontract:
    """Tests for ModelContextIntegritySubcontract model."""

    def _make_version(self) -> ModelSemVer:
        return ModelSemVer(major=1, minor=0, patch=0)

    def test_minimal_construction(self) -> None:
        sub = ModelContextIntegritySubcontract(version=self._make_version())
        assert sub.version == self._make_version()
        assert sub.context_budget_tokens is None
        assert sub.memory_scope == []
        assert sub.tool_scope == []
        assert sub.retrieval_sources == []
        assert sub.return_schema is None
        assert sub.enforcement_level == "WARN"
        assert sub.compression_threshold_tokens is None
        assert sub.compression_time_limit_seconds is None

    def test_full_construction(self) -> None:
        retrieval = ModelRetrievalSource(
            source_type=EnumRetrievalSourceType.VECTOR,
            namespace="qdrant.patterns",
            keys=["code_quality"],
            k=10,
        )
        return_schema = ModelReturnSchema(
            allowed_fields=["status", "pr_url"],
            max_tokens=200,
        )
        sub = ModelContextIntegritySubcontract(
            version=self._make_version(),
            context_budget_tokens=50000,
            memory_scope=["session", "task"],
            tool_scope=["Bash", "Read", "Write", "Edit"],
            retrieval_sources=[retrieval],
            return_schema=return_schema,
            enforcement_level="STRICT",
            compression_threshold_tokens=40000,
            compression_time_limit_seconds=5.0,
        )
        assert sub.context_budget_tokens == 50000
        assert sub.memory_scope == ["session", "task"]
        assert sub.tool_scope == ["Bash", "Read", "Write", "Edit"]
        assert len(sub.retrieval_sources) == 1
        assert sub.retrieval_sources[0].namespace == "qdrant.patterns"
        assert sub.return_schema is not None
        assert sub.return_schema.max_tokens == 200
        assert sub.enforcement_level == "STRICT"
        assert sub.compression_threshold_tokens == 40000
        assert sub.compression_time_limit_seconds == 5.0

    def test_enforcement_level_case_insensitive(self) -> None:
        sub = ModelContextIntegritySubcontract(
            version=self._make_version(),
            enforcement_level="permissive",
        )
        assert sub.enforcement_level == "PERMISSIVE"

    def test_enforcement_level_all_values(self) -> None:
        for level in ["PERMISSIVE", "WARN", "STRICT", "PARANOID"]:
            sub = ModelContextIntegritySubcontract(
                version=self._make_version(),
                enforcement_level=level,
            )
            assert sub.enforcement_level == level

    def test_enforcement_level_invalid_raises(self) -> None:
        with pytest.raises(ModelOnexError):
            ModelContextIntegritySubcontract(
                version=self._make_version(),
                enforcement_level="INVALID",
            )

    def test_context_budget_tokens_minimum(self) -> None:
        with pytest.raises(Exception):
            ModelContextIntegritySubcontract(
                version=self._make_version(),
                context_budget_tokens=0,
            )

    def test_compression_threshold_minimum(self) -> None:
        with pytest.raises(Exception):
            ModelContextIntegritySubcontract(
                version=self._make_version(),
                compression_threshold_tokens=0,
            )

    def test_compression_time_limit_positive(self) -> None:
        with pytest.raises(Exception):
            ModelContextIntegritySubcontract(
                version=self._make_version(),
                compression_time_limit_seconds=0.0,
            )

    def test_version_required(self) -> None:
        with pytest.raises(Exception):
            ModelContextIntegritySubcontract()  # type: ignore[call-arg]


@pytest.mark.unit
class TestModelHandlerContractIntegration:
    """Tests for context_integrity field on ModelHandlerContract."""

    def test_handler_contract_without_context_integrity(self) -> None:
        from omnibase_core.models.contracts.model_handler_contract import (
            ModelHandlerContract,
        )
        from omnibase_core.models.runtime.model_handler_behavior import (
            ModelHandlerBehavior,
        )

        contract = ModelHandlerContract(
            handler_id="node.test.compute",
            name="Test Compute Node",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=ModelHandlerBehavior(
                node_archetype="compute",
                purity="pure",
                idempotent=True,
            ),
            input_model="test.Input",
            output_model="test.Output",
        )
        assert contract.context_integrity is None

    def test_handler_contract_with_context_integrity(self) -> None:
        from omnibase_core.models.contracts.model_handler_contract import (
            ModelHandlerContract,
        )
        from omnibase_core.models.runtime.model_handler_behavior import (
            ModelHandlerBehavior,
        )

        integrity = ModelContextIntegritySubcontract(
            version=ModelSemVer(major=1, minor=0, patch=0),
            context_budget_tokens=100000,
            tool_scope=["Read", "Grep"],
            enforcement_level="STRICT",
        )

        contract = ModelHandlerContract(
            handler_id="node.audit.compute",
            name="Audit Compute Node",
            contract_version=ModelSemVer(major=1, minor=0, patch=0),
            descriptor=ModelHandlerBehavior(
                node_archetype="compute",
                purity="pure",
                idempotent=True,
            ),
            input_model="test.Input",
            output_model="test.Output",
            context_integrity=integrity,
        )
        assert contract.context_integrity is not None
        assert contract.context_integrity.context_budget_tokens == 100000
        assert contract.context_integrity.enforcement_level == "STRICT"
