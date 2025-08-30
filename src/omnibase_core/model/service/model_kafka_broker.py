"""
Kafka Broker Model for ONEX Configuration-Driven Registry System.

This module provides the ModelKafkaBroker for Kafka broker configuration.
Extracted from model_service_configuration.py for modular architecture compliance.

Author: OmniNode Team
"""

from pydantic import BaseModel, Field


class ModelKafkaBroker(BaseModel):
    """Strongly typed Kafka broker configuration."""

    host: str = Field(..., description="Kafka broker hostname")
    port: int = Field(9092, description="Kafka broker port", ge=1, le=65535)

    def to_connection_string(self) -> str:
        """Convert to Kafka connection string format."""
        return f"{self.host}:{self.port}"
