# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelContractPatch."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.contracts.model_capability_provided import (
    ModelCapabilityProvided,
)
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_dependency import ModelDependency
from omnibase_core.models.contracts.model_descriptor_patch import ModelDescriptorPatch
from omnibase_core.models.contracts.model_handler_spec import ModelHandlerSpec
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.contracts.model_reference import ModelReference
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelContractPatch:
    """Tests for ModelContractPatch model."""

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    @pytest.mark.unit
    def test_minimal_patch(self, profile_ref: ModelProfileReference) -> None:
        """Test creating a minimal patch with just extends."""
        patch = ModelContractPatch(extends=profile_ref)
        assert patch.extends == profile_ref
        assert patch.name is None
        assert patch.node_version is None
        assert patch.is_override_only is True
        assert patch.is_new_contract is False

    @pytest.mark.unit
    def test_new_contract_patch(self, profile_ref: ModelProfileReference) -> None:
        """Test creating a new contract patch with identity."""
        version = ModelSemVer(major=1, minor=0, patch=0)
        patch = ModelContractPatch(
            extends=profile_ref,
            name="my_handler",
            node_version=version,
            description="A custom handler",
        )
        assert patch.name == "my_handler"
        assert patch.node_version == version
        assert patch.description == "A custom handler"
        assert patch.is_new_contract is True
        assert patch.is_override_only is False

    @pytest.mark.unit
    def test_extends_required(self) -> None:
        """Test that extends is required."""
        with pytest.raises(ValidationError):
            ModelContractPatch()  # type: ignore[call-arg]

    @pytest.mark.unit
    def test_name_without_version_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that name without version is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                name="my_handler",
                # Missing node_version
            )
        assert "node_version" in str(exc_info.value)

    @pytest.mark.unit
    def test_version_without_name_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that version without name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                node_version=ModelSemVer(major=1, minor=0, patch=0),
                # Missing name
            )
        assert "name" in str(exc_info.value)

    @pytest.mark.unit
    def test_model_overrides(self, profile_ref: ModelProfileReference) -> None:
        """Test input/output model overrides."""
        patch = ModelContractPatch(
            extends=profile_ref,
            input_model=ModelReference(
                module="mypackage.models",
                class_name="InputModel",
            ),
            output_model=ModelReference(
                module="mypackage.models",
                class_name="OutputModel",
            ),
        )
        assert patch.input_model is not None
        assert patch.output_model is not None
        assert patch.input_model.class_name == "InputModel"
        assert patch.output_model.class_name == "OutputModel"

    @pytest.mark.unit
    def test_descriptor_patch(self, profile_ref: ModelProfileReference) -> None:
        """Test nested behavior patch."""
        patch = ModelContractPatch(
            extends=profile_ref,
            descriptor=ModelDescriptorPatch(
                timeout_ms=30000,
                idempotent=True,
            ),
        )
        assert patch.descriptor is not None
        assert patch.descriptor.timeout_ms == 30000
        assert patch.descriptor.idempotent is True

    @pytest.mark.unit
    def test_handlers_add(self, profile_ref: ModelProfileReference) -> None:
        """Test adding handlers."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[
                ModelHandlerSpec(name="http_client", handler_type="http"),
                ModelHandlerSpec(name="kafka_producer", handler_type="kafka"),
            ],
        )
        assert patch.handlers__add is not None
        assert len(patch.handlers__add) == 2
        assert patch.handlers__add[0].name == "http_client"

    @pytest.mark.unit
    def test_handlers_remove(self, profile_ref: ModelProfileReference) -> None:
        """Test removing handlers."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=["old_handler", "deprecated_handler"],
        )
        assert patch.handlers__remove is not None
        assert len(patch.handlers__remove) == 2
        assert "old_handler" in patch.handlers__remove

    @pytest.mark.unit
    def test_dependencies_add(self, profile_ref: ModelProfileReference) -> None:
        """Test adding dependencies."""
        patch = ModelContractPatch(
            extends=profile_ref,
            dependencies__add=[
                ModelDependency(name="ProtocolLogger"),
                ModelDependency(name="ProtocolEventBus"),
            ],
        )
        assert patch.dependencies__add is not None
        assert len(patch.dependencies__add) == 2

    @pytest.mark.unit
    def test_dependencies_remove(self, profile_ref: ModelProfileReference) -> None:
        """Test removing dependencies."""
        patch = ModelContractPatch(
            extends=profile_ref,
            dependencies__remove=["OldProtocol"],
        )
        assert patch.dependencies__remove is not None
        assert "OldProtocol" in patch.dependencies__remove

    @pytest.mark.unit
    def test_consumed_events_add(self, profile_ref: ModelProfileReference) -> None:
        """Test adding consumed events."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__add=["user.created", "order.placed"],
        )
        assert patch.consumed_events__add is not None
        assert "user.created" in patch.consumed_events__add

    @pytest.mark.unit
    def test_consumed_events_remove(self, profile_ref: ModelProfileReference) -> None:
        """Test removing consumed events."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__remove=["deprecated.event"],
        )
        assert patch.consumed_events__remove is not None

    @pytest.mark.unit
    def test_capability_inputs_add(self, profile_ref: ModelProfileReference) -> None:
        """Test adding capability inputs."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=["http", "json"],
        )
        assert patch.capability_inputs__add is not None
        assert "http" in patch.capability_inputs__add

    @pytest.mark.unit
    def test_capability_outputs_add(self, profile_ref: ModelProfileReference) -> None:
        """Test adding capability outputs."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__add=[
                ModelCapabilityProvided(name="event_emit"),
                ModelCapabilityProvided(name="logging", version="1.0.0"),
            ],
        )
        assert patch.capability_outputs__add is not None
        assert len(patch.capability_outputs__add) == 2

    @pytest.mark.unit
    def test_has_list_operations_false(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test has_list_operations when no list operations."""
        patch = ModelContractPatch(extends=profile_ref)
        assert patch.has_list_operations() is False

    @pytest.mark.unit
    def test_has_list_operations_true(self, profile_ref: ModelProfileReference) -> None:
        """Test has_list_operations when list operations present."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[ModelHandlerSpec(name="test", handler_type="test")],
        )
        assert patch.has_list_operations() is True

    @pytest.mark.unit
    def test_get_add_operations(self, profile_ref: ModelProfileReference) -> None:
        """Test get_add_operations method."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[ModelHandlerSpec(name="test", handler_type="test")],
            consumed_events__add=["event.type"],
        )
        adds = patch.get_add_operations()
        assert "handlers" in adds
        assert "consumed_events" in adds
        assert "dependencies" not in adds

    @pytest.mark.unit
    def test_get_remove_operations(self, profile_ref: ModelProfileReference) -> None:
        """Test get_remove_operations method."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=["old_handler"],
            dependencies__remove=["OldDep"],
        )
        removes = patch.get_remove_operations()
        assert "handlers" in removes
        assert "dependencies" in removes
        assert "consumed_events" not in removes

    @pytest.mark.unit
    def test_extra_fields_rejected(self, profile_ref: ModelProfileReference) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelContractPatch(
                extends=profile_ref,
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

    @pytest.mark.unit
    def test_repr_new_contract(self, profile_ref: ModelProfileReference) -> None:
        """Test repr for new contract."""
        patch = ModelContractPatch(
            extends=profile_ref,
            name="my_handler",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        repr_str = repr(patch)
        assert "new=" in repr_str
        assert "my_handler" in repr_str

    @pytest.mark.unit
    def test_repr_override(self, profile_ref: ModelProfileReference) -> None:
        """Test repr for override patch."""
        patch = ModelContractPatch(extends=profile_ref)
        repr_str = repr(patch)
        assert "override" in repr_str
        assert "compute_pure" in repr_str

    @pytest.mark.unit
    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "extends": {"profile": "compute_pure", "version": "1.0.0"},
            "name": "my_handler",
            "node_version": {"major": 1, "minor": 0, "patch": 0},
            "descriptor": {"timeout_ms": 5000},
        }
        patch = ModelContractPatch.model_validate(data)
        assert patch.name == "my_handler"
        assert patch.descriptor is not None
        assert patch.descriptor.timeout_ms == 5000

    @pytest.mark.unit
    def test_full_patch(self, profile_ref: ModelProfileReference) -> None:
        """Test a comprehensive patch with many fields."""
        patch = ModelContractPatch(
            extends=profile_ref,
            name="comprehensive_handler",
            node_version=ModelSemVer(major=2, minor=0, patch=0),
            description="A comprehensive handler for testing",
            input_model=ModelReference(
                module="mypackage.models",
                class_name="InputModel",
            ),
            output_model=ModelReference(
                module="mypackage.models",
                class_name="OutputModel",
            ),
            descriptor=ModelDescriptorPatch(
                purity="pure",
                idempotent=True,
                timeout_ms=10000,
                concurrency_policy="parallel_ok",
            ),
            handlers__add=[
                ModelHandlerSpec(name="http_client", handler_type="http"),
            ],
            dependencies__add=[
                ModelDependency(name="ProtocolLogger"),
            ],
            consumed_events__add=["user.created"],
            capability_inputs__add=["http"],
            capability_outputs__add=[
                ModelCapabilityProvided(name="event_emit"),
            ],
        )

        assert patch.is_new_contract is True
        assert patch.has_list_operations() is True
        assert len(patch.get_add_operations()) == 5
        assert patch.descriptor is not None
        assert patch.descriptor.has_overrides() is True


@pytest.mark.unit
class TestModelContractPatchValidation:
    """Tests for ModelContractPatch field validation and edge cases."""

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    # =========================================================================
    # handlers__remove validation
    # =========================================================================

    @pytest.mark.unit
    def test_handlers_remove_empty_string_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty strings in handlers__remove are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                handlers__remove=["valid_handler", ""],
            )
        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    def test_handlers_remove_whitespace_only_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that whitespace-only strings in handlers__remove are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                handlers__remove=["valid_handler", "   "],
            )
        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    def test_handlers_remove_invalid_chars_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that invalid characters in handlers__remove are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                handlers__remove=["invalid-handler"],
            )
        assert "alphanumeric" in str(exc_info.value)

    @pytest.mark.unit
    def test_handlers_remove_normalized_to_lowercase(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that handler names in handlers__remove are normalized to lowercase."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=["HTTP_Client", "KafkaProducer"],
        )
        assert patch.handlers__remove is not None
        assert patch.handlers__remove == ["http_client", "kafkaproducer"]

    @pytest.mark.unit
    def test_handlers_remove_whitespace_stripped(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that whitespace is stripped from handler names."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=["  valid_handler  ", "\tother_handler\n"],
        )
        assert patch.handlers__remove is not None
        assert patch.handlers__remove == ["valid_handler", "other_handler"]

    # =========================================================================
    # dependencies__remove validation
    # =========================================================================

    @pytest.mark.unit
    def test_dependencies_remove_empty_string_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty strings in dependencies__remove are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                dependencies__remove=["ProtocolLogger", ""],
            )
        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    def test_dependencies_remove_too_short_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that too-short dependency names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                dependencies__remove=["X"],
            )
        # Shared validation uses "must be at least N characters" format
        assert "must be at least 2 characters" in str(exc_info.value)

    # =========================================================================
    # consumed_events validation
    # =========================================================================

    @pytest.mark.unit
    def test_consumed_events_add_empty_string_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty strings in consumed_events__add are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                consumed_events__add=["user.created", ""],
            )
        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    def test_consumed_events_remove_empty_string_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty strings in consumed_events__remove are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                consumed_events__remove=["user.deleted", "   "],
            )
        assert "cannot be empty" in str(exc_info.value)

    # =========================================================================
    # capability_inputs validation
    # =========================================================================

    @pytest.mark.unit
    def test_capability_inputs_add_empty_string_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty strings in capability_inputs__add are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_inputs__add=["http", ""],
            )
        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_inputs_add_invalid_chars_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that invalid characters in capability_inputs__add are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_inputs__add=["http-client"],
            )
        assert "alphanumeric" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_inputs_normalized_to_lowercase(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability names are normalized to lowercase."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=["HTTP", "DatabaseRead"],
        )
        assert patch.capability_inputs__add is not None
        assert patch.capability_inputs__add == ["http", "databaseread"]

    @pytest.mark.unit
    def test_capability_inputs_remove_normalized_to_lowercase(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_inputs__remove names are normalized to lowercase."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__remove=["HTTP_Client", "CacheWrite"],
        )
        assert patch.capability_inputs__remove is not None
        assert patch.capability_inputs__remove == ["http_client", "cachewrite"]

    # =========================================================================
    # capability_outputs__remove validation
    # =========================================================================

    @pytest.mark.unit
    def test_capability_outputs_remove_empty_string_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty strings in capability_outputs__remove are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_outputs__remove=["event_emit", ""],
            )
        assert "cannot be empty" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_outputs_remove_invalid_chars_rejected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that invalid characters in capability_outputs__remove are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_outputs__remove=["event-emit"],
            )
        assert "alphanumeric" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_outputs_remove_normalized_to_lowercase(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_outputs__remove names are normalized to lowercase."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__remove=["EventEmit", "HTTP_Response"],
        )
        assert patch.capability_outputs__remove is not None
        assert patch.capability_outputs__remove == ["eventemit", "http_response"]


@pytest.mark.unit
class TestEmptyListNormalization:
    """Tests for empty list normalization to None."""

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    # =========================================================================
    # handlers__add / handlers__remove
    # =========================================================================

    @pytest.mark.unit
    def test_handlers_add_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty handlers__add list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[],
        )
        assert patch.handlers__add is None

    @pytest.mark.unit
    def test_handlers_remove_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty handlers__remove list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=[],
        )
        assert patch.handlers__remove is None

    # =========================================================================
    # dependencies__add / dependencies__remove
    # =========================================================================

    @pytest.mark.unit
    def test_dependencies_add_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty dependencies__add list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            dependencies__add=[],
        )
        assert patch.dependencies__add is None

    @pytest.mark.unit
    def test_dependencies_remove_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty dependencies__remove list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            dependencies__remove=[],
        )
        assert patch.dependencies__remove is None

    # =========================================================================
    # consumed_events__add / consumed_events__remove
    # =========================================================================

    @pytest.mark.unit
    def test_consumed_events_add_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty consumed_events__add list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__add=[],
        )
        assert patch.consumed_events__add is None

    @pytest.mark.unit
    def test_consumed_events_remove_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty consumed_events__remove list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__remove=[],
        )
        assert patch.consumed_events__remove is None

    # =========================================================================
    # capability_inputs__add / capability_inputs__remove
    # =========================================================================

    @pytest.mark.unit
    def test_capability_inputs_add_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty capability_inputs__add list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=[],
        )
        assert patch.capability_inputs__add is None

    @pytest.mark.unit
    def test_capability_inputs_remove_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty capability_inputs__remove list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__remove=[],
        )
        assert patch.capability_inputs__remove is None

    # =========================================================================
    # capability_outputs__add / capability_outputs__remove
    # =========================================================================

    @pytest.mark.unit
    def test_capability_outputs_add_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty capability_outputs__add list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__add=[],
        )
        assert patch.capability_outputs__add is None

    @pytest.mark.unit
    def test_capability_outputs_remove_empty_list_becomes_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty capability_outputs__remove list is normalized to None."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__remove=[],
        )
        assert patch.capability_outputs__remove is None

    # =========================================================================
    # Comprehensive / Integration tests
    # =========================================================================

    @pytest.mark.unit
    def test_all_empty_lists_become_none(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that all empty lists are normalized to None simultaneously."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[],
            handlers__remove=[],
            dependencies__add=[],
            dependencies__remove=[],
            consumed_events__add=[],
            consumed_events__remove=[],
            capability_inputs__add=[],
            capability_inputs__remove=[],
            capability_outputs__add=[],
            capability_outputs__remove=[],
        )
        assert patch.handlers__add is None
        assert patch.handlers__remove is None
        assert patch.dependencies__add is None
        assert patch.dependencies__remove is None
        assert patch.consumed_events__add is None
        assert patch.consumed_events__remove is None
        assert patch.capability_inputs__add is None
        assert patch.capability_inputs__remove is None
        assert patch.capability_outputs__add is None
        assert patch.capability_outputs__remove is None
        # Also verify that has_list_operations returns False
        assert patch.has_list_operations() is False

    @pytest.mark.unit
    def test_non_empty_lists_preserved(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that non-empty lists are preserved correctly."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=["old_handler"],
            consumed_events__add=["user.created"],
            capability_inputs__add=["http"],
        )
        assert patch.handlers__remove is not None
        assert len(patch.handlers__remove) == 1
        assert patch.consumed_events__add is not None
        assert len(patch.consumed_events__add) == 1
        assert patch.capability_inputs__add is not None
        assert len(patch.capability_inputs__add) == 1

    @pytest.mark.unit
    def test_mixed_empty_and_nonempty_lists(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that empty lists become None while non-empty are preserved."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[],  # Should become None
            handlers__remove=["old_handler"],  # Should be preserved
            dependencies__add=[],  # Should become None
            consumed_events__add=["user.created"],  # Should be preserved
        )
        assert patch.handlers__add is None
        assert patch.handlers__remove is not None
        assert patch.dependencies__add is None
        assert patch.consumed_events__add is not None


@pytest.mark.unit
class TestModelContractPatchConflicts:
    """Tests for ModelContractPatch add/remove conflict detection."""

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    # =========================================================================
    # handlers conflict detection
    # =========================================================================

    @pytest.mark.unit
    def test_handlers_conflict_detected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that adding and removing the same handler is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                handlers__add=[
                    ModelHandlerSpec(name="http_client", handler_type="http"),
                ],
                handlers__remove=["http_client"],
            )
        assert "Conflicting" in str(exc_info.value)
        assert "handlers" in str(exc_info.value)

    @pytest.mark.unit
    def test_handlers_conflict_case_insensitive(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that handler conflict detection is case-insensitive."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                handlers__add=[
                    ModelHandlerSpec(name="HTTP_Client", handler_type="http"),
                ],
                handlers__remove=["http_client"],
            )
        assert "Conflicting" in str(exc_info.value)

    @pytest.mark.unit
    def test_handlers_no_conflict_different_names(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that different handler names don't conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[
                ModelHandlerSpec(name="http_client", handler_type="http"),
            ],
            handlers__remove=["kafka_producer"],
        )
        assert patch.handlers__add is not None
        assert patch.handlers__remove is not None

    @pytest.mark.unit
    def test_handlers_add_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that handlers__add without handlers__remove has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[
                ModelHandlerSpec(name="http_client", handler_type="http"),
            ],
        )
        assert patch.handlers__add is not None
        assert patch.handlers__remove is None

    @pytest.mark.unit
    def test_handlers_remove_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that handlers__remove without handlers__add has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=["old_handler"],
        )
        assert patch.handlers__remove is not None
        assert patch.handlers__add is None

    # =========================================================================
    # dependencies conflict detection
    # =========================================================================

    @pytest.mark.unit
    def test_dependencies_conflict_detected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that adding and removing the same dependency is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                dependencies__add=[
                    ModelDependency(name="ProtocolLogger"),
                ],
                dependencies__remove=["ProtocolLogger"],
            )
        assert "Conflicting" in str(exc_info.value)
        assert "dependencies" in str(exc_info.value)

    @pytest.mark.unit
    def test_dependencies_no_conflict_different_names(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that different dependency names don't conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            dependencies__add=[
                ModelDependency(name="ProtocolLogger"),
            ],
            dependencies__remove=["OldProtocol"],
        )
        assert patch.dependencies__add is not None
        assert patch.dependencies__remove is not None

    # =========================================================================
    # consumed_events conflict detection
    # =========================================================================

    @pytest.mark.unit
    def test_consumed_events_conflict_detected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that adding and removing the same event is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                consumed_events__add=["user.created"],
                consumed_events__remove=["user.created"],
            )
        assert "Conflicting" in str(exc_info.value)
        assert "consumed_events" in str(exc_info.value)

    @pytest.mark.unit
    def test_consumed_events_no_conflict_different_events(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that different event types don't conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__add=["user.created"],
            consumed_events__remove=["user.deleted"],
        )
        assert patch.consumed_events__add is not None
        assert patch.consumed_events__remove is not None

    @pytest.mark.unit
    def test_consumed_events_add_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that consumed_events__add without remove has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__add=["user.created", "order.placed"],
        )
        assert patch.consumed_events__add is not None
        assert patch.consumed_events__remove is None

    @pytest.mark.unit
    def test_consumed_events_remove_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that consumed_events__remove without add has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__remove=["deprecated.event"],
        )
        assert patch.consumed_events__remove is not None
        assert patch.consumed_events__add is None

    # =========================================================================
    # capability_inputs conflict detection
    # =========================================================================

    @pytest.mark.unit
    def test_capability_inputs_conflict_detected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that adding and removing the same capability input is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_inputs__add=["http"],
                capability_inputs__remove=["http"],
            )
        assert "Conflicting" in str(exc_info.value)
        assert "capability_inputs" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_inputs_conflict_case_insensitive(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_inputs conflict detection is case-insensitive."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_inputs__add=["HTTP"],
                capability_inputs__remove=["http"],
            )
        assert "Conflicting" in str(exc_info.value)
        assert "capability_inputs" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_inputs_no_conflict_different_capabilities(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that different capability inputs don't conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=["http"],
            capability_inputs__remove=["database_read"],
        )
        assert patch.capability_inputs__add is not None
        assert patch.capability_inputs__remove is not None

    @pytest.mark.unit
    def test_capability_inputs_add_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_inputs__add without remove has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=["http", "json"],
        )
        assert patch.capability_inputs__add is not None
        assert patch.capability_inputs__remove is None

    @pytest.mark.unit
    def test_capability_inputs_remove_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_inputs__remove without add has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__remove=["deprecated_capability"],
        )
        assert patch.capability_inputs__remove is not None
        assert patch.capability_inputs__add is None

    @pytest.mark.unit
    def test_capability_inputs_conflict_multiple_items(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that multiple capability inputs conflicts are detected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_inputs__add=["http", "json", "xml"],
                capability_inputs__remove=["json", "xml"],
            )
        assert "Conflicting" in str(exc_info.value)
        # At least one conflicting capability should be mentioned
        error_str = str(exc_info.value)
        assert "json" in error_str or "xml" in error_str

    # =========================================================================
    # capability_outputs conflict detection
    # =========================================================================

    @pytest.mark.unit
    def test_capability_outputs_conflict_detected(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that adding and removing the same capability output is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_outputs__add=[
                    ModelCapabilityProvided(name="event_emit"),
                ],
                capability_outputs__remove=["event_emit"],
            )
        assert "Conflicting" in str(exc_info.value)
        assert "capability_outputs" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_outputs_conflict_case_insensitive(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_outputs conflict detection is case-insensitive."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_outputs__add=[
                    ModelCapabilityProvided(name="EventEmit"),
                ],
                capability_outputs__remove=["eventemit"],
            )
        assert "Conflicting" in str(exc_info.value)
        assert "capability_outputs" in str(exc_info.value)

    @pytest.mark.unit
    def test_capability_outputs_no_conflict_different_capabilities(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that different capability outputs don't conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__add=[
                ModelCapabilityProvided(name="event_emit"),
            ],
            capability_outputs__remove=["logging"],
        )
        assert patch.capability_outputs__add is not None
        assert patch.capability_outputs__remove is not None

    @pytest.mark.unit
    def test_capability_outputs_add_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_outputs__add without remove has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__add=[
                ModelCapabilityProvided(name="event_emit"),
                ModelCapabilityProvided(name="logging"),
            ],
        )
        assert patch.capability_outputs__add is not None
        assert patch.capability_outputs__remove is None

    @pytest.mark.unit
    def test_capability_outputs_remove_only_no_conflict(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that capability_outputs__remove without add has no conflict."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_outputs__remove=["deprecated_capability"],
        )
        assert patch.capability_outputs__remove is not None
        assert patch.capability_outputs__add is None

    @pytest.mark.unit
    def test_capability_outputs_conflict_multiple_items(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that multiple capability outputs conflicts are detected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                capability_outputs__add=[
                    ModelCapabilityProvided(name="event_emit"),
                    ModelCapabilityProvided(name="logging"),
                ],
                capability_outputs__remove=["event_emit", "logging"],
            )
        assert "Conflicting" in str(exc_info.value)

    # =========================================================================
    # Mixed conflict detection
    # =========================================================================

    @pytest.mark.unit
    def test_multiple_list_type_conflicts(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that conflicts across multiple list types are all reported."""
        with pytest.raises(ValidationError) as exc_info:
            ModelContractPatch(
                extends=profile_ref,
                handlers__add=[
                    ModelHandlerSpec(name="http_client", handler_type="http"),
                ],
                handlers__remove=["http_client"],
                consumed_events__add=["user.created"],
                consumed_events__remove=["user.created"],
            )
        error_str = str(exc_info.value)
        assert "Conflicting" in error_str
        assert "handlers" in error_str
        assert "consumed_events" in error_str

    @pytest.mark.unit
    def test_no_conflicts_with_different_items_in_all_lists(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test that non-conflicting items in all list types work."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[
                ModelHandlerSpec(name="new_handler", handler_type="http"),
            ],
            handlers__remove=["old_handler"],
            dependencies__add=[
                ModelDependency(name="ProtocolLogger"),
            ],
            dependencies__remove=["OldProtocol"],
            consumed_events__add=["new.event"],
            consumed_events__remove=["old.event"],
            capability_inputs__add=["new_capability"],
            capability_inputs__remove=["old_capability"],
            capability_outputs__add=[
                ModelCapabilityProvided(name="new_output"),
            ],
            capability_outputs__remove=["old_output"],
        )
        assert patch.has_list_operations() is True
        assert len(patch.get_add_operations()) == 5
        assert len(patch.get_remove_operations()) == 5
