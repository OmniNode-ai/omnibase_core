# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelHandlerDescriptor."""

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_capability import EnumHandlerCapability
from omnibase_core.enums.enum_handler_command_type import EnumHandlerCommandType
from omnibase_core.enums.enum_handler_role import EnumHandlerRole
from omnibase_core.enums.enum_handler_type import EnumHandlerType
from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.handlers.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.handlers.model_handler_descriptor import (
    ModelHandlerDescriptor,
)
from omnibase_core.models.handlers.model_identifier import ModelIdentifier
from omnibase_core.models.handlers.model_packaging_metadata_ref import (
    ModelPackagingMetadataRef,
)
from omnibase_core.models.handlers.model_security_metadata_ref import (
    ModelSecurityMetadataRef,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
class TestModelHandlerDescriptorInstantiation:
    """Tests for ModelHandlerDescriptor instantiation."""

    def test_basic_instantiation_with_required_fields(self) -> None:
        """Test creating descriptor with all required fields."""
        handler_name = ModelIdentifier(namespace="onex", name="compute-handler")
        handler_version = ModelSemVer(major=1, minor=0, patch=0)

        descriptor = ModelHandlerDescriptor(
            handler_name=handler_name,
            handler_version=handler_version,
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )

        assert descriptor.handler_name == handler_name
        assert descriptor.handler_version == handler_version
        assert descriptor.handler_role == EnumHandlerRole.COMPUTE_HANDLER
        assert descriptor.handler_type == EnumHandlerType.NAMED
        assert descriptor.handler_type_category == EnumHandlerTypeCategory.COMPUTE
        assert descriptor.is_adapter is False  # Default
        assert descriptor.capabilities == []  # Default factory
        assert descriptor.commands_accepted == []  # Default factory
        assert descriptor.import_path is None
        assert descriptor.artifact_ref is None
        assert descriptor.security_metadata_ref is None
        assert descriptor.packaging_metadata_ref is None

    def test_instantiation_with_all_fields(self) -> None:
        """Test creating descriptor with all optional fields."""
        handler_name = ModelIdentifier(namespace="onex", name="kafka-adapter")
        handler_version = ModelSemVer(major=1, minor=2, patch=3)
        artifact_ref = ModelArtifactRef(ref="artifact://kafka-adapter-v1")
        security_ref = ModelSecurityMetadataRef(ref="security://kafka-adapter")
        packaging_ref = ModelPackagingMetadataRef(ref="pkg://kafka-adapter")

        descriptor = ModelHandlerDescriptor(
            handler_name=handler_name,
            handler_version=handler_version,
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.KAFKA,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=True,
            capabilities=[
                EnumHandlerCapability.STREAM,
                EnumHandlerCapability.ASYNC,
            ],
            commands_accepted=[
                EnumHandlerCommandType.EXECUTE,
                EnumHandlerCommandType.HEALTH_CHECK,
            ],
            import_path="omnibase_infra.adapters.kafka.KafkaAdapter",
            artifact_ref=artifact_ref,
            security_metadata_ref=security_ref,
            packaging_metadata_ref=packaging_ref,
        )

        assert descriptor.handler_name == handler_name
        assert descriptor.handler_version == handler_version
        assert descriptor.handler_role == EnumHandlerRole.INFRA_HANDLER
        assert descriptor.handler_type == EnumHandlerType.KAFKA
        assert descriptor.handler_type_category == EnumHandlerTypeCategory.EFFECT
        assert descriptor.is_adapter is True
        assert len(descriptor.capabilities) == 2
        assert EnumHandlerCapability.STREAM in descriptor.capabilities
        assert len(descriptor.commands_accepted) == 2
        assert descriptor.import_path == "omnibase_infra.adapters.kafka.KafkaAdapter"
        assert descriptor.artifact_ref == artifact_ref
        assert descriptor.security_metadata_ref == security_ref
        assert descriptor.packaging_metadata_ref == packaging_ref


@pytest.mark.unit
class TestModelHandlerDescriptorAdapterPolicy:
    """Tests for is_adapter policy tag and validation."""

    def test_is_adapter_false_default(self) -> None:
        """Test that is_adapter defaults to False."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.is_adapter is False

    def test_is_adapter_false_with_any_category(self) -> None:
        """Test is_adapter=False works with any handler_type_category."""
        # COMPUTE category
        descriptor1 = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="compute"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            is_adapter=False,
        )
        assert descriptor1.is_adapter is False
        assert descriptor1.handler_type_category == EnumHandlerTypeCategory.COMPUTE

        # EFFECT category
        descriptor2 = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="db-handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.DATABASE,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=False,
        )
        assert descriptor2.is_adapter is False
        assert descriptor2.handler_type_category == EnumHandlerTypeCategory.EFFECT

        # NONDETERMINISTIC_COMPUTE category
        descriptor3 = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="random-handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
            is_adapter=False,
        )
        assert descriptor3.is_adapter is False
        assert (
            descriptor3.handler_type_category
            == EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE
        )

    def test_is_adapter_true_with_effect_category(self) -> None:
        """Test is_adapter=True works with EFFECT category."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="kafka-adapter"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.KAFKA,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=True,
        )
        assert descriptor.is_adapter is True
        assert descriptor.handler_type_category == EnumHandlerTypeCategory.EFFECT

    def test_is_adapter_true_with_compute_category_raises_error(self) -> None:
        """Test is_adapter=True with COMPUTE category raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="bad-adapter"),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.COMPUTE_HANDLER,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
                is_adapter=True,  # This should fail validation
            )
        error = exc_info.value
        assert "is_adapter=True" in str(error)
        assert "handler_type_category=compute" in str(error)
        assert "MUST have handler_type_category=EFFECT" in str(error)

    def test_is_adapter_true_with_nondeterministic_category_raises_error(self) -> None:
        """Test is_adapter=True with NONDETERMINISTIC_COMPUTE raises ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="bad-adapter"),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.COMPUTE_HANDLER,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
                is_adapter=True,  # This should fail validation
            )
        error = exc_info.value
        assert "is_adapter=True" in str(error)
        assert "MUST have handler_type_category=EFFECT" in str(error)


@pytest.mark.unit
class TestModelHandlerDescriptorEnumFields:
    """Tests for enum field acceptance."""

    def test_all_handler_roles_accepted(self) -> None:
        """Test all EnumHandlerRole values are accepted."""
        for role in EnumHandlerRole:
            descriptor = ModelHandlerDescriptor(
                handler_name=ModelIdentifier(
                    namespace="onex", name=f"handler-{role.value}"
                ),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=role,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            )
            assert descriptor.handler_role == role

    def test_all_handler_types_accepted(self) -> None:
        """Test all EnumHandlerType values are accepted."""
        for handler_type in EnumHandlerType:
            descriptor = ModelHandlerDescriptor(
                handler_name=ModelIdentifier(
                    namespace="onex", name=f"handler-{handler_type.value}"
                ),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.INFRA_HANDLER,
                handler_type=handler_type,
                handler_type_category=EnumHandlerTypeCategory.EFFECT,
            )
            assert descriptor.handler_type == handler_type

    def test_all_handler_type_categories_accepted(self) -> None:
        """Test all EnumHandlerTypeCategory values are accepted."""
        for category in EnumHandlerTypeCategory:
            descriptor = ModelHandlerDescriptor(
                handler_name=ModelIdentifier(
                    namespace="onex", name=f"handler-{category.value}"
                ),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.COMPUTE_HANDLER,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=category,
            )
            assert descriptor.handler_type_category == category

    def test_all_handler_capabilities_accepted(self) -> None:
        """Test all EnumHandlerCapability values are accepted in list."""
        all_capabilities = list(EnumHandlerCapability)
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="capable-handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.HTTP,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            capabilities=all_capabilities,
        )
        assert set(descriptor.capabilities) == set(all_capabilities)

    def test_all_handler_command_types_accepted(self) -> None:
        """Test all EnumHandlerCommandType values are accepted in list."""
        all_commands = list(EnumHandlerCommandType)
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="full-handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.NODE_HANDLER,
            handler_type=EnumHandlerType.EVENT_BUS,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            commands_accepted=all_commands,
        )
        assert set(descriptor.commands_accepted) == set(all_commands)


@pytest.mark.unit
class TestModelHandlerDescriptorOptionalFields:
    """Tests for optional fields."""

    def test_import_path_optional(self) -> None:
        """Test import_path is optional."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.import_path is None

    def test_import_path_accepted(self) -> None:
        """Test import_path is accepted when provided."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            import_path="mypackage.handlers.MyHandler",
        )
        assert descriptor.import_path == "mypackage.handlers.MyHandler"

    def test_artifact_ref_optional(self) -> None:
        """Test artifact_ref is optional."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.artifact_ref is None

    def test_artifact_ref_accepted(self) -> None:
        """Test artifact_ref is accepted when provided."""
        artifact = ModelArtifactRef(ref="artifact://handler-v1")
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            artifact_ref=artifact,
        )
        assert descriptor.artifact_ref == artifact

    def test_security_metadata_ref_optional(self) -> None:
        """Test security_metadata_ref is optional."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.security_metadata_ref is None

    def test_security_metadata_ref_accepted(self) -> None:
        """Test security_metadata_ref is accepted when provided."""
        security = ModelSecurityMetadataRef(ref="security://handler-policy")
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            security_metadata_ref=security,
        )
        assert descriptor.security_metadata_ref == security

    def test_packaging_metadata_ref_optional(self) -> None:
        """Test packaging_metadata_ref is optional."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.packaging_metadata_ref is None

    def test_packaging_metadata_ref_accepted(self) -> None:
        """Test packaging_metadata_ref is accepted when provided."""
        packaging = ModelPackagingMetadataRef(ref="pkg://handler-v1")
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            packaging_metadata_ref=packaging,
        )
        assert descriptor.packaging_metadata_ref == packaging


@pytest.mark.unit
class TestModelHandlerDescriptorDefaultFactories:
    """Tests for default_factory fields."""

    def test_capabilities_default_empty_list(self) -> None:
        """Test capabilities defaults to empty list via default_factory."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.capabilities == []
        assert isinstance(descriptor.capabilities, list)

    def test_commands_accepted_default_empty_list(self) -> None:
        """Test commands_accepted defaults to empty list via default_factory."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.commands_accepted == []
        assert isinstance(descriptor.commands_accepted, list)

    def test_default_lists_are_independent(self) -> None:
        """Test that default lists are independent between instances."""
        descriptor1 = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler1"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        descriptor2 = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler2"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        # They should be equal (both empty) but not the same object
        assert descriptor1.capabilities == descriptor2.capabilities
        # Note: frozen model means we can't modify to test independence,
        # but default_factory ensures separate instances


@pytest.mark.unit
class TestModelHandlerDescriptorImmutability:
    """Tests for ModelHandlerDescriptor frozen immutability."""

    def test_frozen_immutability_handler_name(self) -> None:
        """Test that handler_name cannot be modified (frozen model)."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        new_name = ModelIdentifier(namespace="vendor", name="modified")
        with pytest.raises(ValidationError, match="frozen"):
            descriptor.handler_name = new_name  # type: ignore[misc]

    def test_frozen_immutability_handler_role(self) -> None:
        """Test that handler_role cannot be modified (frozen model)."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        with pytest.raises(ValidationError, match="frozen"):
            descriptor.handler_role = EnumHandlerRole.INFRA_HANDLER  # type: ignore[misc]

    def test_frozen_immutability_is_adapter(self) -> None:
        """Test that is_adapter cannot be modified (frozen model)."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.KAFKA,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=True,
        )
        with pytest.raises(ValidationError, match="frozen"):
            descriptor.is_adapter = False  # type: ignore[misc]


@pytest.mark.unit
class TestModelHandlerDescriptorExtraFields:
    """Tests for extra field rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelHandlerDescriptor(
                handler_name=ModelIdentifier(namespace="onex", name="handler"),
                handler_version=ModelSemVer(major=1, minor=0, patch=0),
                handler_role=EnumHandlerRole.COMPUTE_HANDLER,
                handler_type=EnumHandlerType.NAMED,
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelHandlerDescriptorSerialization:
    """Tests for ModelHandlerDescriptor serialization."""

    def test_model_dump_minimal(self) -> None:
        """Test model_dump with minimal fields."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        data = descriptor.model_dump()

        assert data["handler_name"]["namespace"] == "onex"
        assert data["handler_name"]["name"] == "handler"
        assert data["handler_version"]["major"] == 1
        assert data["handler_role"] == "compute_handler"
        assert data["handler_type"] == "named"
        assert data["handler_type_category"] == "compute"
        assert data["is_adapter"] is False
        assert data["capabilities"] == []
        assert data["commands_accepted"] == []

    def test_model_dump_roundtrip(self) -> None:
        """Test serialization and deserialization roundtrip."""
        original = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="kafka-adapter"),
            handler_version=ModelSemVer(major=2, minor=1, patch=3),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.KAFKA,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=True,
            capabilities=[EnumHandlerCapability.STREAM, EnumHandlerCapability.ASYNC],
            commands_accepted=[EnumHandlerCommandType.EXECUTE],
            import_path="mypackage.adapters.KafkaAdapter",
        )
        data = original.model_dump()
        restored = ModelHandlerDescriptor(**data)

        assert restored.handler_name == original.handler_name
        assert restored.handler_version == original.handler_version
        assert restored.handler_role == original.handler_role
        assert restored.handler_type == original.handler_type
        assert restored.handler_type_category == original.handler_type_category
        assert restored.is_adapter == original.is_adapter
        assert restored.capabilities == original.capabilities
        assert restored.commands_accepted == original.commands_accepted
        assert restored.import_path == original.import_path


@pytest.mark.unit
class TestModelHandlerDescriptorUseCases:
    """Tests for real-world use cases from the model documentation."""

    def test_kafka_ingress_adapter(self) -> None:
        """Test creating a Kafka ingress adapter descriptor."""
        adapter = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="kafka-ingress"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.KAFKA,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=True,  # Platform plumbing
            capabilities=[EnumHandlerCapability.STREAM, EnumHandlerCapability.ASYNC],
            import_path="omnibase_infra.adapters.kafka_ingress.KafkaIngressAdapter",
        )
        assert adapter.is_adapter is True
        assert adapter.handler_type == EnumHandlerType.KAFKA
        assert adapter.handler_type_category == EnumHandlerTypeCategory.EFFECT

    def test_database_handler_not_adapter(self) -> None:
        """Test creating a database handler (NOT an adapter)."""
        db_handler = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="postgres-handler"),
            handler_version=ModelSemVer(major=2, minor=1, patch=0),
            handler_role=EnumHandlerRole.INFRA_HANDLER,
            handler_type=EnumHandlerType.DATABASE,
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            is_adapter=False,  # Full handler - needs secrets, broader permissions
            capabilities=[
                EnumHandlerCapability.RETRY,
                EnumHandlerCapability.IDEMPOTENT,
            ],
            import_path="omnibase_infra.handlers.postgres_handler.PostgresHandler",
        )
        assert db_handler.is_adapter is False
        assert db_handler.handler_type == EnumHandlerType.DATABASE
        assert db_handler.handler_type_category == EnumHandlerTypeCategory.EFFECT

    def test_pure_compute_handler(self) -> None:
        """Test creating a pure compute handler."""
        validator = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="schema-validator"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            capabilities=[
                EnumHandlerCapability.VALIDATE,
                EnumHandlerCapability.CACHE,
            ],
            import_path="omnibase_core.handlers.schema_validator.SchemaValidator",
        )
        assert validator.is_adapter is False
        assert validator.handler_role == EnumHandlerRole.COMPUTE_HANDLER
        assert validator.handler_type_category == EnumHandlerTypeCategory.COMPUTE


@pytest.mark.unit
class TestModelHandlerDescriptorInstantiationMethods:
    """Tests for instantiation helper methods."""

    def test_has_instantiation_method_with_import_path(self) -> None:
        """Test has_instantiation_method returns True when import_path is set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            import_path="mypackage.handlers.MyHandler",
        )
        assert descriptor.has_instantiation_method is True

    def test_has_instantiation_method_with_artifact_ref(self) -> None:
        """Test has_instantiation_method returns True when artifact_ref is set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            artifact_ref=ModelArtifactRef(ref="artifact://handler-v1"),
        )
        assert descriptor.has_instantiation_method is True

    def test_has_instantiation_method_with_both(self) -> None:
        """Test has_instantiation_method returns True when both are set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            import_path="mypackage.handlers.MyHandler",
            artifact_ref=ModelArtifactRef(ref="artifact://handler-v1"),
        )
        assert descriptor.has_instantiation_method is True

    def test_has_instantiation_method_metadata_only(self) -> None:
        """Test has_instantiation_method returns False for metadata-only descriptors."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.has_instantiation_method is False

    def test_can_instantiate_via_import_true(self) -> None:
        """Test can_instantiate_via_import returns True when import_path is set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            import_path="mypackage.handlers.MyHandler",
        )
        assert descriptor.can_instantiate_via_import() is True

    def test_can_instantiate_via_import_false(self) -> None:
        """Test can_instantiate_via_import returns False when import_path is None."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.can_instantiate_via_import() is False

    def test_can_instantiate_via_import_with_only_artifact_ref(self) -> None:
        """Test can_instantiate_via_import returns False when only artifact_ref is set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            artifact_ref=ModelArtifactRef(ref="artifact://handler-v1"),
        )
        assert descriptor.can_instantiate_via_import() is False

    def test_can_instantiate_via_artifact_true(self) -> None:
        """Test can_instantiate_via_artifact returns True when artifact_ref is set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            artifact_ref=ModelArtifactRef(ref="artifact://handler-v1"),
        )
        assert descriptor.can_instantiate_via_artifact() is True

    def test_can_instantiate_via_artifact_false(self) -> None:
        """Test can_instantiate_via_artifact returns False when artifact_ref is None."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.can_instantiate_via_artifact() is False

    def test_can_instantiate_via_artifact_with_only_import_path(self) -> None:
        """Test can_instantiate_via_artifact returns False when only import_path is set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            import_path="mypackage.handlers.MyHandler",
        )
        assert descriptor.can_instantiate_via_artifact() is False

    def test_both_instantiation_methods_set(self) -> None:
        """Test both methods return True when both are set."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="handler"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            import_path="mypackage.handlers.MyHandler",
            artifact_ref=ModelArtifactRef(ref="artifact://handler-v1"),
        )
        assert descriptor.can_instantiate_via_import() is True
        assert descriptor.can_instantiate_via_artifact() is True
        assert descriptor.has_instantiation_method is True

    def test_metadata_only_descriptor_all_methods_false(self) -> None:
        """Test all instantiation methods return False for metadata-only descriptors."""
        descriptor = ModelHandlerDescriptor(
            handler_name=ModelIdentifier(namespace="onex", name="metadata-only"),
            handler_version=ModelSemVer(major=1, minor=0, patch=0),
            handler_role=EnumHandlerRole.COMPUTE_HANDLER,
            handler_type=EnumHandlerType.NAMED,
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
        )
        assert descriptor.can_instantiate_via_import() is False
        assert descriptor.can_instantiate_via_artifact() is False
        assert descriptor.has_instantiation_method is False
