"""Kafka Hook Processor Utility

Handles Kafka event processing and hook management for Claude Code tool captures.
Follows ONEX utility patterns with strong typing and single responsibility.
"""

import asyncio
import json
import os
from typing import Callable, List, Optional

from omnibase_core.model.hook_events.model_onex_hook_event import \
    ModelOnexHookEvent
from omnibase_core.models.model_event_statistics import ModelEventStatistics
from omnibase_core.models.model_kafka_config import ModelKafkaConfig
from omnibase_core.models.model_kafka_config_response import \
    ModelKafkaConfigResponse

try:
    from aiokafka import AIOKafkaConsumer

    AIOKAFKA_AVAILABLE = True
except ImportError:
    AIOKAFKA_AVAILABLE = False
    AIOKafkaConsumer = None


class UtilityKafkaHookProcessor:
    """Kafka hook event processing utility.

    Responsibilities:
    - Kafka consumer/producer management
    - Hook event processing and correlation
    - Event filtering and transformation
    - Real-time event broadcasting
    """

    def __init__(
        self, bootstrap_servers: Optional[str] = None, group_id: Optional[str] = None
    ):
        """Initialize Kafka hook processor.

        Args:
            bootstrap_servers: Kafka servers, defaults to environment variable
            group_id: Consumer group ID, defaults to standard group
        """
        try:
            # Initialize basic state FIRST - this must always succeed
            self.consumer: Optional[AIOKafkaConsumer] = None
            self.hook_events: List[ModelOnexHookEvent] = []  # Now using unified model
            self.event_callbacks: List[Callable[[ModelOnexHookEvent], None]] = []
            self.consumer_task: Optional[asyncio.Task[None]] = None
            self.enabled = False  # Start disabled, enable only if everything works
            self.config = None

            if not AIOKAFKA_AVAILABLE:
                print("⚠️ aiokafka not available, Kafka functionality disabled")
                return

            # Configuration from environment or parameters
            servers = bootstrap_servers or os.getenv("KAFKA_BOOTSTRAP_SERVERS")
            if not servers:
                print("⚠️ KAFKA_BOOTSTRAP_SERVERS not set, Kafka functionality disabled")
                return

            # Use a fixed consumer group for the causal graph service
            # This ensures a single consumer gets ALL partitions
            default_group_id = "omnimemory-causal-graph-capture"
            self.config = ModelKafkaConfig(
                bootstrap_servers=servers, group_id=group_id or default_group_id
            )
            print(f"📊 Using consumer group: {self.config.group_id}")

            # Only enable if all configuration succeeds
            self.enabled = True

            print(
                f"✅ Kafka hook processor initialized: {self.config.bootstrap_servers}"
            )

        except Exception as e:
            # CRITICAL: Ensure basic state is always initialized even if config fails
            print(f"⚠️ Kafka hook processor initialization failed: {e}")
            self.consumer = None
            self.hook_events = []
            self.event_callbacks = []
            self.consumer_task = None
            self.enabled = False
            self.config = None
            print(
                "🛡️ Kafka processor initialized in safe mode - Claude Code will continue working"
            )

    async def start(self) -> bool:
        """Start the Kafka consumer and event processing.

        Returns:
            True if started successfully, False otherwise
        """
        if not self.enabled:
            print("⚠️ Kafka processor disabled, skipping start")
            return False

        try:
            # Initialize consumer
            if not self.config:
                print("❌ Configuration not available")
                return False

            self.consumer = AIOKafkaConsumer(
                *self.config.topics,
                bootstrap_servers=self.config.bootstrap_servers,
                group_id=self.config.group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                # Consumer group stability settings (aiokafka compatible)
                session_timeout_ms=30000,  # 30 seconds
                heartbeat_interval_ms=10000,  # 10 seconds
                max_poll_interval_ms=300000,  # 5 minutes
                max_poll_records=100,  # Reduce batch size
                # Offset management
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,  # 5 seconds
                auto_offset_reset="latest",  # Start from latest messages in production
                # Note: Partition assignment strategy is automatic in aiokafka
                # Single consumer in a group automatically gets all partitions
                # Connection settings
                retry_backoff_ms=100,
                request_timeout_ms=40000,  # 40 seconds
            )

            # Start consumer
            await self.consumer.start()

            # Log partition assignments
            print("📊 Partition assignments:")
            try:
                assignment = self.consumer.assignment()
                print(f"   Assignment type: {type(assignment)}")
                print(f"   Assignment: {assignment}")
                # Assignment is a set of TopicPartition objects
                topics_dict: dict[str, List[int]] = {}
                for tp in assignment:
                    if tp.topic not in topics_dict:
                        topics_dict[tp.topic] = []
                    topics_dict[tp.topic].append(tp.partition)

                for topic, partitions in topics_dict.items():
                    print(f"   Topic: {topic} -> Partitions: {sorted(partitions)}")

                if not assignment:
                    print(
                        "   ⚠️ No partitions assigned yet - will be assigned after first poll"
                    )
            except Exception as e:
                print(f"   Could not get assignment yet: {e}")

            # Start background processing task
            self.consumer_task = asyncio.create_task(self._consume_events())

            print(
                f"🎉 Kafka consumer started for topics: {self.config.topics if self.config else []}"
            )
            return True

        except Exception as e:
            print(f"❌ Failed to start Kafka consumer: {e}")
            print(
                f"   Bootstrap servers: {self.config.bootstrap_servers if self.config else 'None'}"
            )
            print(f"   Group ID: {self.config.group_id if self.config else 'None'}")
            print(f"   Topics: {self.config.topics if self.config else 'None'}")
            self.consumer = None
            return False

    async def stop(self) -> None:
        """Stop the Kafka consumer and cleanup resources."""
        if not self.enabled:
            return

        try:
            # Cancel background task
            if self.consumer_task:
                self.consumer_task.cancel()
                try:
                    await self.consumer_task
                except asyncio.CancelledError:
                    pass
                self.consumer_task = None

            # Stop consumer
            if self.consumer:
                await self.consumer.stop()
                self.consumer = None

            print("🛑 Kafka consumer stopped")

        except Exception as e:
            print(f"❌ Error stopping Kafka consumer: {e}")

    def add_event_callback(
        self, callback: Callable[[ModelOnexHookEvent], None]
    ) -> None:
        """Add a callback function to receive hook events.

        Args:
            callback: Function to call when events are processed
        """
        self.event_callbacks.append(callback)
        print(f"📢 Added event callback: {callback.__name__}")

    def remove_event_callback(
        self, callback: Callable[[ModelOnexHookEvent], None]
    ) -> None:
        """Remove an event callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)
            print(f"🗑️ Removed event callback: {callback.__name__}")

    def get_recent_events(self, limit: int = 100) -> List[ModelOnexHookEvent]:
        """Get recent hook events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent unified hook events
        """
        try:
            # Ensure hook_events is properly initialized
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []
                return []

            return self.hook_events[-limit:] if self.hook_events else []
        except Exception as e:
            print(f"⚠️ Error getting recent events: {e}")
            # Ensure hook_events is properly initialized
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []
            return []

    def get_event_statistics(self) -> ModelEventStatistics:
        """Get event processing statistics.

        Returns:
            Event statistics model
        """
        try:
            # Ensure hook_events is properly initialized
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []

            if not self.hook_events:
                return ModelEventStatistics(
                    total_events=0,
                    pre_execution_events=0,
                    post_execution_events=0,
                    unique_tools=0,
                    kafka_status="connected" if self.consumer else "disconnected",
                    enabled=self.enabled,
                )

            pre_count = sum(
                1
                for event in self.hook_events
                if hasattr(event, "event_type") and event.event_type == "pre-execution"
            )
            post_count = sum(
                1
                for event in self.hook_events
                if hasattr(event, "event_type") and event.event_type == "post-execution"
            )
            unique_tools = len(
                set(
                    event.tool_name
                    for event in self.hook_events
                    if hasattr(event, "tool_name") and event.tool_name
                )
            )

            return ModelEventStatistics(
                total_events=len(self.hook_events),
                pre_execution_events=pre_count,
                post_execution_events=post_count,
                unique_tools=unique_tools,
                kafka_status="connected" if self.consumer else "disconnected",
                enabled=self.enabled,
            )

        except Exception as e:
            print(f"⚠️ Error getting event statistics: {e}")
            # Ensure hook_events is properly initialized
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []

            return ModelEventStatistics(
                total_events=0,
                pre_execution_events=0,
                post_execution_events=0,
                unique_tools=0,
                kafka_status="connected" if self.consumer else "disconnected",
                enabled=self.enabled,
            )

    def filter_events_by_tool(self, tool_name: str) -> List[ModelOnexHookEvent]:
        """Filter events by tool name.

        Args:
            tool_name: Name of the tool to filter by

        Returns:
            List of unified events for the specified tool
        """
        try:
            # Ensure hook_events is not None and is iterable
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []
                return []

            return [
                event
                for event in self.hook_events
                if hasattr(event, "tool_name") and event.tool_name == tool_name
            ]
        except Exception as e:
            print(f"⚠️ Error filtering events by tool '{tool_name}': {e}")
            # Ensure hook_events is properly initialized
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []
            return []

    def filter_events_by_session(self, session_id: str) -> List[ModelOnexHookEvent]:
        """Filter events by session ID.

        Args:
            session_id: Claude session ID to filter by

        Returns:
            List of unified events for the specified session
        """
        try:
            # Ensure hook_events is not None and is iterable
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []
                return []

            return [
                event
                for event in self.hook_events
                if hasattr(event, "session_id") and event.session_id == session_id
            ]
        except Exception as e:
            print(f"⚠️ Error filtering events by session '{session_id}': {e}")
            # Ensure hook_events is properly initialized
            if not hasattr(self, "hook_events") or self.hook_events is None:
                self.hook_events = []
            return []

    async def _consume_events(self) -> None:
        """Background task to consume and process Kafka events."""
        if not self.consumer:
            return

        try:
            async for message in self.consumer:
                try:
                    # DEBUG: Log raw Kafka message
                    print("=== KAFKA MESSAGE DEBUG ===")
                    print(f"Topic: {message.topic}")
                    print(f"Raw message.value: {json.dumps(message.value, indent=2)}")
                    print("==============================")

                    # Parse as unified ModelOnexHookEvent (all events should use this format)
                    try:
                        unified_event = ModelOnexHookEvent.model_validate(message.value)
                        print(
                            f"✅ Parsed unified event: topic={message.topic}, event_type={unified_event.event_type}, tool={unified_event.tool_name or 'N/A'}"
                        )
                    except Exception as parse_error:
                        print(
                            f"❌ Failed to parse message from topic {message.topic}: {parse_error}"
                        )
                        print(f"   Raw message: {message.value}")
                        # Skip malformed messages
                        continue

                    # Store the unified event (with memory limit) - ensure hook_events is always initialized
                    try:
                        if not hasattr(self, "hook_events") or self.hook_events is None:
                            self.hook_events = []

                        self.hook_events.append(unified_event)

                        if (
                            self.config
                            and len(self.hook_events) > self.config.max_events_in_memory
                        ):
                            self.hook_events.pop(0)
                    except Exception as store_error:
                        print(f"⚠️ Error storing hook event: {store_error}")
                        # Reinitialize hook_events if there's an issue
                        self.hook_events = [
                            unified_event
                        ]  # At least store the current event

                    # Notify callbacks with unified event
                    for callback in self.event_callbacks:
                        try:
                            callback(unified_event)
                        except Exception as e:
                            print(
                                f"❌ Error in event callback {callback.__name__}: {e}"
                            )

                except Exception as parse_error:
                    print(f"❌ FAILED TO PARSE MESSAGE FROM TOPIC {message.topic}:")
                    print(f"   Parse error: {parse_error}")
                    print(f"   Raw message: {message.value}")
                    # Continue processing other messages

        except asyncio.CancelledError:
            print("🛑 Event consumption cancelled")
        except Exception as e:
            print(f"❌ Error consuming Kafka events: {e}")

    def is_connected(self) -> bool:
        """Check if Kafka consumer is connected and running.

        Returns:
            True if connected and consuming
        """
        return (
            self.enabled
            and self.consumer is not None
            and self.consumer_task is not None
            and not self.consumer_task.done()
        )

    def get_configuration(self) -> ModelKafkaConfigResponse:
        """Get current Kafka configuration.

        Returns:
            Configuration response model
        """
        if not self.enabled:
            return ModelKafkaConfigResponse(
                enabled=False, reason="Kafka not available or configured"
            )

        return ModelKafkaConfigResponse(
            enabled=True,
            bootstrap_servers=self.config.bootstrap_servers if self.config else None,
            group_id=self.config.group_id if self.config else None,
            topics=self.config.topics if self.config else None,
            max_events_in_memory=(
                self.config.max_events_in_memory if self.config else None
            ),
            connected=self.is_connected(),
        )
