"""Model for managing Kafka consumers."""

from typing import Dict

from aiokafka import AIOKafkaConsumer
from pydantic import BaseModel, Field


class ModelConsumerMap(BaseModel):
    """
    Strongly-typed mapping for Kafka consumer management.

    Replaces Dict[str, AIOKafkaConsumer] to comply with ONEX
    standards requiring specific typed models.
    """

    consumers: Dict[str, AIOKafkaConsumer] = Field(
        default_factory=dict, description="Map of topic names to Kafka consumers"
    )

    class Config:
        # Allow AIOKafkaConsumer objects in Pydantic model
        arbitrary_types_allowed = True

    def add_consumer(self, topic: str, consumer: AIOKafkaConsumer) -> None:
        """Add a consumer for a topic."""
        self.consumers[topic] = consumer

    def get_consumer(self, topic: str) -> AIOKafkaConsumer:
        """Get consumer for a specific topic."""
        return self.consumers.get(topic)

    def remove_consumer(self, topic: str) -> bool:
        """Remove a consumer."""
        if topic in self.consumers:
            del self.consumers[topic]
            return True
        return False

    def get_all_consumers(self) -> Dict[str, AIOKafkaConsumer]:
        """Get all consumers."""
        return self.consumers

    def has_consumer(self, topic: str) -> bool:
        """Check if consumer exists for topic."""
        return topic in self.consumers

    def count(self) -> int:
        """Get total number of consumers."""
        return len(self.consumers)

    def clear(self) -> None:
        """Remove all consumers."""
        self.consumers.clear()
