"""
MixinIntentPublisher - Coordination I/O capability for ONEX nodes.

This mixin provides intent publishing capability for nodes that need to
coordinate actions without performing direct domain I/O. Intents are
published to coordination topics for execution by dedicated intent executor nodes.

Architecture:
    Node (pure logic) → publish_event_intent() → Kafka (intent topic)
        → IntentExecutor → Kafka (domain topic)

Usage:
    class MyReducer(MixinIntentPublisher):
        def __init__(self, container):
            self._init_intent_publisher(container)

        async def execute(self):
            result = self._do_pure_logic()

            # Publish intent instead of direct event
            await self.publish_event_intent(
                target_topic=TOPIC_MY_EVENT,
                target_key="my-key",
                event=my_event_model
            )

            return result

Subcontract:
    Requires: contracts/intent_publisher.yaml

Dependencies:
    - kafka_client service (for intent publishing)
    - ModelOnexEnvelopeV1 (from omnibase_core)

Part of omnibase_core framework - provides coordination I/O for all ONEX nodes
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.events.model_intent_events import (
    TOPIC_EVENT_PUBLISH_INTENT,
    ModelEventPublishIntent,
)
from omnibase_core.models.model_intent_publish_result import ModelIntentPublishResult


class MixinIntentPublisher:
    """
    Mixin providing intent publishing capability for ONEX nodes.

    This mixin allows nodes to coordinate actions (like publishing events)
    without performing direct domain I/O. Instead, nodes publish "intents"
    to a coordination topic, which are executed by dedicated IntentExecutor nodes.

    Key Principles:
        - Domain logic stays pure (no direct I/O)
        - Coordination I/O is explicit (via this mixin)
        - Intents are traceable (correlation IDs, timestamps)
        - Execution is async and decoupled

    Architecture:
        The intent pattern separates "what to do" from "doing it":

        1. Node builds intent (pure data)
        2. Mixin publishes intent to coordination topic
        3. IntentExecutor consumes intent
        4. IntentExecutor performs actual I/O via EFFECT nodes
        5. IntentExecutor publishes execution result

    Benefits:
        - Testability: Pure node logic without Kafka mocks
        - Reusability: Same logic works with different effects
        - Observability: All intents are logged on Kafka
        - Resilience: Intent execution can retry independently

    Example:
        class MetricsReducer(MixinIntentPublisher):
            def __init__(self, container):
                self._init_intent_publisher(container)

            async def execute_reduction(self, events):
                # Pure aggregation
                metrics = self._aggregate(events)

                # Build event (pure)
                event = MetricsRecordedEvent(...)

                # Publish intent (coordination I/O)
                await self.publish_event_intent(
                    target_topic=TOPIC_METRICS,
                    target_key=str(metrics.id),
                    event=event
                )

                return metrics

    Subcontract Configuration:
        Add to node's contract.yaml:

        subcontracts:
          refs:
            - "./contracts/intent_publisher.yaml"

        mixins:
          - "MixinIntentPublisher"

    Thread Safety:
        This mixin is async-safe. Multiple concurrent calls to
        publish_event_intent() are supported.
    """

    # Kafka topic for intent events
    INTENT_TOPIC: str = TOPIC_EVENT_PUBLISH_INTENT

    def _init_intent_publisher(self, container: Any) -> None:
        """
        Initialize intent publishing capability.

        Must be called in node's __init__ after super().__init__().

        Args:
            container: ModelContainer with services

        Raises:
            ValueError: If required kafka_client service is missing

        Example:
            def __init__(self, container):
                super().__init__(container)
                self._init_intent_publisher(container)
        """
        self._intent_kafka_client = container.get_service("kafka_client")
        if self._intent_kafka_client is None:
            raise OnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="MixinIntentPublisher requires 'kafka_client' service in container. "
                "Ensure kafka_client is registered before initializing nodes.",
            )

        # Store container for access to other services if needed
        self._intent_container = container

    async def publish_event_intent(
        self,
        target_topic: str,
        target_key: str,
        event: BaseModel,
        correlation_id: UUID | None = None,
        priority: int = 5,
    ) -> ModelIntentPublishResult:
        """
        Publish an intent to publish an event.

        This is coordination I/O, not domain I/O. The intent will be
        consumed by an IntentExecutor that performs the actual publishing
        via proper EFFECT nodes.

        Args:
            target_topic: Kafka topic where event should be published
            target_key: Kafka key for the event
            event: Event to publish (Pydantic model with model_dump())
            correlation_id: Optional correlation ID (generated if not provided)
            priority: Intent priority 1-10 (1=highest, default=5)

        Returns:
            ModelIntentPublishResult with intent_id and metadata

        Raises:
            AttributeError: If event doesn't have model_dump() method
            ValueError: If priority is out of range
            Exception: If Kafka publishing fails

        Example:
            result = await self.publish_event_intent(
                target_topic="dev.omninode.metrics.v1",
                target_key="metrics-123",
                event=MetricsRecordedEvent(...)
            )
            print(f"Intent published: {result.intent_id}")
        """
        # Validate inputs
        if not hasattr(event, "model_dump"):
            raise OnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Event must be a Pydantic model with model_dump() method. "
                f"Got: {type(event).__name__}",
            )

        if not (1 <= priority <= 10):
            raise OnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Priority must be 1-10, got: {priority}",
            )

        # Generate IDs
        intent_id = uuid4()
        correlation_id = correlation_id or uuid4()
        published_at = datetime.now(UTC)

        # Build intent payload
        intent = ModelEventPublishIntent(
            intent_id=intent_id,
            correlation_id=correlation_id,
            created_at=published_at,
            created_by=self.__class__.__name__,
            target_topic=target_topic,
            target_key=target_key,
            target_event_type=event.__class__.__name__,
            target_event_payload=event.model_dump(),
            priority=priority,
        )

        # Wrap in ModelOnexEnvelopeV1 for standard event format
        try:
            from omnibase_core.models.core import ModelOnexEnvelopeV1
            from omnibase_core.primitives.model_semver import ModelSemVer

            envelope = ModelOnexEnvelopeV1(
                envelope_version=ModelSemVer(major=1, minor=0, patch=0),
                correlation_id=correlation_id,
                event_id=intent_id,
                event_type="EVENT_PUBLISH_INTENT",
                timestamp=published_at,
                source_service=f"omninode_bridge.{self.__class__.__name__}",
                payload=intent.model_dump(),
            )

            envelope_json = envelope.model_dump_json()

        except ImportError:
            # Fallback if ModelOnexEnvelopeV1 not available (should not happen)
            envelope_json = intent.model_dump_json()

        # Publish to intent topic (coordination I/O)
        await self._intent_kafka_client.publish(
            topic=self.INTENT_TOPIC,
            key=str(intent_id),
            value=envelope_json,
        )

        return ModelIntentPublishResult(
            intent_id=intent_id,
            published_at=published_at,
            target_topic=target_topic,
            correlation_id=correlation_id,
        )
