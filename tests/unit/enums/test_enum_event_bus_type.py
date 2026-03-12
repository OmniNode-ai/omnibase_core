# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EnumEventBusType (OMN-4794)."""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_event_bus_type import EnumEventBusType


class TestEnumEventBusTypeValues:
    """Test EnumEventBusType members and string values."""

    @pytest.mark.unit
    def test_kafka_value(self) -> None:
        """KAFKA member has value 'kafka'."""
        assert EnumEventBusType.KAFKA.value == "kafka"

    @pytest.mark.unit
    def test_inmemory_value(self) -> None:
        """INMEMORY member has value 'inmemory'."""
        assert EnumEventBusType.INMEMORY.value == "inmemory"

    @pytest.mark.unit
    def test_cloud_value(self) -> None:
        """CLOUD member has value 'cloud'."""
        assert EnumEventBusType.CLOUD.value == "cloud"

    @pytest.mark.unit
    def test_str_returns_value(self) -> None:
        """str() returns the enum value (StrValueHelper mixin)."""
        assert str(EnumEventBusType.KAFKA) == "kafka"
        assert str(EnumEventBusType.INMEMORY) == "inmemory"


class TestEnumEventBusTypeProductionSafety:
    """Test is_production_safe and requires_broker properties."""

    @pytest.mark.unit
    def test_kafka_is_production_safe(self) -> None:
        """KAFKA is production safe."""
        assert EnumEventBusType.KAFKA.is_production_safe is True

    @pytest.mark.unit
    def test_cloud_is_production_safe(self) -> None:
        """CLOUD is production safe."""
        assert EnumEventBusType.CLOUD.is_production_safe is True

    @pytest.mark.unit
    def test_inmemory_not_production_safe(self) -> None:
        """INMEMORY is NOT production safe."""
        assert EnumEventBusType.INMEMORY.is_production_safe is False

    @pytest.mark.unit
    def test_kafka_requires_broker(self) -> None:
        """KAFKA requires an external broker."""
        assert EnumEventBusType.KAFKA.requires_broker is True

    @pytest.mark.unit
    def test_cloud_requires_broker(self) -> None:
        """CLOUD requires an external broker."""
        assert EnumEventBusType.CLOUD.requires_broker is True

    @pytest.mark.unit
    def test_inmemory_does_not_require_broker(self) -> None:
        """INMEMORY does not require an external broker."""
        assert EnumEventBusType.INMEMORY.requires_broker is False


class TestSubscriptionCreatedEventValidator:
    """Test that ModelSubscriptionCreatedEvent forbids INMEMORY in production."""

    @pytest.mark.unit
    def test_inmemory_forbidden_in_production(self) -> None:
        """Raises ValueError when bus_type=INMEMORY and env=production."""
        from uuid import uuid4

        from pydantic import ValidationError

        from omnibase_core.models.events.model_subscription_created_event import (
            ModelSubscriptionCreatedEvent,
        )

        with pytest.raises(
            ValidationError, match="INMEMORY is forbidden in production"
        ):
            ModelSubscriptionCreatedEvent.create(
                node_id=uuid4(),
                topic="test.topic",
                event_bus_type=EnumEventBusType.INMEMORY,
                env="production",
            )

    @pytest.mark.unit
    def test_inmemory_allowed_in_development(self) -> None:
        """INMEMORY is allowed when env=development (default)."""
        from uuid import uuid4

        from omnibase_core.models.events.model_subscription_created_event import (
            ModelSubscriptionCreatedEvent,
        )

        event = ModelSubscriptionCreatedEvent.create(
            node_id=uuid4(),
            topic="test.topic",
            event_bus_type=EnumEventBusType.INMEMORY,
            env="development",
        )
        assert event.event_bus_type == EnumEventBusType.INMEMORY

    @pytest.mark.unit
    def test_kafka_allowed_in_production(self) -> None:
        """KAFKA is allowed in production."""
        from uuid import uuid4

        from omnibase_core.models.events.model_subscription_created_event import (
            ModelSubscriptionCreatedEvent,
        )

        event = ModelSubscriptionCreatedEvent.create(
            node_id=uuid4(),
            topic="test.topic",
            event_bus_type=EnumEventBusType.KAFKA,
            env="production",
        )
        assert event.event_bus_type == EnumEventBusType.KAFKA


class TestSubscriptionCreatedEventValidatorNormalization:
    """Test that env string normalization closes bypass vectors."""

    @pytest.mark.unit
    def test_inmemory_forbidden_with_uppercase_production(self) -> None:
        """Raises ValueError when env='Production' (mixed case)."""
        from uuid import uuid4

        from pydantic import ValidationError

        from omnibase_core.models.events.model_subscription_created_event import (
            ModelSubscriptionCreatedEvent,
        )

        with pytest.raises(
            ValidationError, match="INMEMORY is forbidden in production"
        ):
            ModelSubscriptionCreatedEvent.create(
                node_id=uuid4(),
                topic="test.topic",
                event_bus_type=EnumEventBusType.INMEMORY,
                env="Production",
            )

    @pytest.mark.unit
    def test_inmemory_forbidden_with_whitespace_production(self) -> None:
        """Raises ValueError when env=' production ' (leading/trailing whitespace)."""
        from uuid import uuid4

        from pydantic import ValidationError

        from omnibase_core.models.events.model_subscription_created_event import (
            ModelSubscriptionCreatedEvent,
        )

        with pytest.raises(
            ValidationError, match="INMEMORY is forbidden in production"
        ):
            ModelSubscriptionCreatedEvent.create(
                node_id=uuid4(),
                topic="test.topic",
                event_bus_type=EnumEventBusType.INMEMORY,
                env=" production ",
            )


class TestRuntimeReadyEventValidator:
    """Test that ModelRuntimeReadyEvent forbids INMEMORY in production."""

    @pytest.mark.unit
    def test_inmemory_forbidden_in_production(self) -> None:
        """Raises ValueError when bus_type=INMEMORY and env=production."""
        from pydantic import ValidationError

        from omnibase_core.models.events.model_runtime_ready_event import (
            ModelRuntimeReadyEvent,
        )

        with pytest.raises(
            ValidationError, match="INMEMORY is forbidden in production"
        ):
            ModelRuntimeReadyEvent.create(
                event_bus_type=EnumEventBusType.INMEMORY,
                env="production",
            )

    @pytest.mark.unit
    def test_kafka_allowed_in_production(self) -> None:
        """KAFKA is allowed in production."""
        from omnibase_core.models.events.model_runtime_ready_event import (
            ModelRuntimeReadyEvent,
        )

        event = ModelRuntimeReadyEvent.create(
            event_bus_type=EnumEventBusType.KAFKA,
            env="production",
        )
        assert event.event_bus_type == EnumEventBusType.KAFKA

    @pytest.mark.unit
    def test_default_env_is_development(self) -> None:
        """Default env is development — INMEMORY allowed without env arg."""
        from omnibase_core.models.events.model_runtime_ready_event import (
            ModelRuntimeReadyEvent,
        )

        event = ModelRuntimeReadyEvent.create(
            event_bus_type=EnumEventBusType.INMEMORY,
        )
        assert event.env == "development"
        assert event.event_bus_type == EnumEventBusType.INMEMORY


class TestRuntimeReadyEventValidatorNormalization:
    """Test that env string normalization closes bypass vectors."""

    @pytest.mark.unit
    def test_inmemory_forbidden_with_uppercase_production(self) -> None:
        """Raises ValueError when env='PRODUCTION' (all caps)."""
        from pydantic import ValidationError

        from omnibase_core.models.events.model_runtime_ready_event import (
            ModelRuntimeReadyEvent,
        )

        with pytest.raises(
            ValidationError, match="INMEMORY is forbidden in production"
        ):
            ModelRuntimeReadyEvent.create(
                event_bus_type=EnumEventBusType.INMEMORY,
                env="PRODUCTION",
            )

    @pytest.mark.unit
    def test_inmemory_forbidden_with_whitespace_production(self) -> None:
        """Raises ValueError when env=' production ' (leading/trailing whitespace)."""
        from pydantic import ValidationError

        from omnibase_core.models.events.model_runtime_ready_event import (
            ModelRuntimeReadyEvent,
        )

        with pytest.raises(
            ValidationError, match="INMEMORY is forbidden in production"
        ):
            ModelRuntimeReadyEvent.create(
                event_bus_type=EnumEventBusType.INMEMORY,
                env=" production ",
            )
