"""
Gateway Contract Model for ONEX Architecture.

Defines the contract structure for Gateway nodes that handle message routing,
response aggregation, and network coordination patterns.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from omnibase_core.core.contracts.model_contract_base import ModelContractBase
from omnibase_core.core.subcontracts.model_routing_subcontract import (
    ModelRoutingSubcontract,
)


class ModelContractGateway(ModelContractBase):
    """
    Contract model for Gateway nodes in ONEX architecture.

    Gateway nodes handle:
    - Message routing and forwarding
    - Response aggregation patterns
    - Network coordination and discovery
    - Load balancing and failover
    - Protocol translation and bridging
    """

    # Gateway-specific configuration
    routing_subcontract: Optional[ModelRoutingSubcontract] = Field(
        default=None, description="Message routing and forwarding configuration"
    )

    max_concurrent_connections: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum concurrent connections to handle",
    )

    timeout_ms: int = Field(
        default=30000, ge=1000, le=300000, description="Request timeout in milliseconds"
    )

    load_balancing_enabled: bool = Field(
        default=True, description="Whether to enable load balancing across endpoints"
    )

    circuit_breaker_enabled: bool = Field(
        default=True, description="Whether to enable circuit breaker pattern"
    )

    response_aggregation_enabled: bool = Field(
        default=False,
        description="Whether to aggregate responses from multiple sources",
    )

    protocol_translation: Optional[Dict[str, str]] = Field(
        default=None, description="Protocol translation mapping (source -> target)"
    )

    def validate_node_specific_config(self, contract_data: Dict) -> None:
        """
        Validate Gateway-specific configuration requirements.

        Args:
            contract_data: Full contract data for validation

        Raises:
            ValueError: If Gateway contract violates architectural constraints
        """
        # Gateway nodes must have routing capabilities
        if not contract_data.get("routing_subcontract"):
            if not self.routing_subcontract:
                raise ValueError(
                    "Gateway nodes must specify routing_subcontract for message forwarding"
                )

        # Validate timeout configuration
        timeout = contract_data.get("timeout_ms", self.timeout_ms)
        if timeout < 1000:
            raise ValueError(
                "Gateway timeout must be at least 1000ms for reliable operations"
            )

        # Validate connection limits
        max_conn = contract_data.get(
            "max_concurrent_connections", self.max_concurrent_connections
        )
        if max_conn > 10000:
            raise ValueError(
                "Gateway connection limit cannot exceed 10000 for stability"
            )

        # Protocol translation validation
        protocol_trans = contract_data.get("protocol_translation")
        if protocol_trans and not isinstance(protocol_trans, dict):
            raise ValueError("protocol_translation must be a dictionary mapping")

    class Config:
        """Pydantic model configuration."""

        arbitrary_types_allowed = True
        validate_assignment = True
