# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
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


class TestModelContractPatch:
    """Tests for ModelContractPatch model."""

    @pytest.fixture
    def profile_ref(self) -> ModelProfileReference:
        """Create a profile reference fixture."""
        return ModelProfileReference(profile="compute_pure", version="1.0.0")

    def test_minimal_patch(self, profile_ref: ModelProfileReference) -> None:
        """Test creating a minimal patch with just extends."""
        patch = ModelContractPatch(extends=profile_ref)
        assert patch.extends == profile_ref
        assert patch.name is None
        assert patch.node_version is None
        assert patch.is_override_only is True
        assert patch.is_new_contract is False

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

    def test_extends_required(self) -> None:
        """Test that extends is required."""
        with pytest.raises(ValidationError):
            ModelContractPatch()  # type: ignore[call-arg]

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

    def test_descriptor_patch(self, profile_ref: ModelProfileReference) -> None:
        """Test nested descriptor patch."""
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

    def test_handlers_remove(self, profile_ref: ModelProfileReference) -> None:
        """Test removing handlers."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__remove=["old_handler", "deprecated_handler"],
        )
        assert patch.handlers__remove is not None
        assert len(patch.handlers__remove) == 2
        assert "old_handler" in patch.handlers__remove

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

    def test_dependencies_remove(self, profile_ref: ModelProfileReference) -> None:
        """Test removing dependencies."""
        patch = ModelContractPatch(
            extends=profile_ref,
            dependencies__remove=["OldProtocol"],
        )
        assert patch.dependencies__remove is not None
        assert "OldProtocol" in patch.dependencies__remove

    def test_consumed_events_add(self, profile_ref: ModelProfileReference) -> None:
        """Test adding consumed events."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__add=["user.created", "order.placed"],
        )
        assert patch.consumed_events__add is not None
        assert "user.created" in patch.consumed_events__add

    def test_consumed_events_remove(self, profile_ref: ModelProfileReference) -> None:
        """Test removing consumed events."""
        patch = ModelContractPatch(
            extends=profile_ref,
            consumed_events__remove=["deprecated.event"],
        )
        assert patch.consumed_events__remove is not None

    def test_capability_inputs_add(self, profile_ref: ModelProfileReference) -> None:
        """Test adding capability inputs."""
        patch = ModelContractPatch(
            extends=profile_ref,
            capability_inputs__add=["http", "json"],
        )
        assert patch.capability_inputs__add is not None
        assert "http" in patch.capability_inputs__add

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

    def test_has_list_operations_false(
        self, profile_ref: ModelProfileReference
    ) -> None:
        """Test has_list_operations when no list operations."""
        patch = ModelContractPatch(extends=profile_ref)
        assert patch.has_list_operations() is False

    def test_has_list_operations_true(self, profile_ref: ModelProfileReference) -> None:
        """Test has_list_operations when list operations present."""
        patch = ModelContractPatch(
            extends=profile_ref,
            handlers__add=[ModelHandlerSpec(name="test", handler_type="test")],
        )
        assert patch.has_list_operations() is True

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

    def test_extra_fields_rejected(self, profile_ref: ModelProfileReference) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError):
            ModelContractPatch(
                extends=profile_ref,
                extra_field="not_allowed",  # type: ignore[call-arg]
            )

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

    def test_repr_override(self, profile_ref: ModelProfileReference) -> None:
        """Test repr for override patch."""
        patch = ModelContractPatch(extends=profile_ref)
        repr_str = repr(patch)
        assert "override" in repr_str
        assert "compute_pure" in repr_str

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
