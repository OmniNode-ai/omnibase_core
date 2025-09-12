"""
Gateway Contract Model for ONEX Architecture.

Defines the contract structure for Gateway nodes that handle message routing,
response aggregation, and network coordination patterns.
"""

from pydantic import Field

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
    routing_subcontract: ModelRoutingSubcontract | None = Field(
        default=None,
        description="Message routing and forwarding configuration",
    )

    max_concurrent_connections: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Maximum concurrent connections to handle",
    )

    timeout_ms: int = Field(
        default=30000,
        ge=1000,
        le=300000,
        description="Request timeout in milliseconds",
    )

    load_balancing_enabled: bool = Field(
        default=True,
        description="Whether to enable load balancing across endpoints",
    )

    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Whether to enable circuit breaker pattern",
    )

    response_aggregation_enabled: bool = Field(
        default=False,
        description="Whether to aggregate responses from multiple sources",
    )

    protocol_translation: dict[str, str] | None = Field(
        default=None,
        description="Protocol translation mapping (source -> target)",
    )

    def validate_node_specific_config(self) -> None:
        """
        Validate Gateway-specific configuration requirements.

        Raises:
            ValueError: If Gateway contract violates architectural constraints
        """
        # Gateway nodes must have routing capabilities
        if not self.routing_subcontract:
            raise ValueError(
                "Gateway nodes must specify routing_subcontract for message forwarding",
            )

        # Validate timeout configuration
        if self.timeout_ms < 1000:
            raise ValueError(
                "Gateway timeout must be at least 1000ms for reliable operations",
            )

        # Validate connection limits
        if self.max_concurrent_connections > 10000:
            raise ValueError(
                "Gateway connection limit cannot exceed 10000 for stability",
            )

        # Protocol translation validation
        if self.protocol_translation and not isinstance(
            self.protocol_translation,
            dict,
        ):
            raise ValueError("protocol_translation must be a dictionary mapping")

    class Config:
        """Pydantic model configuration."""

        arbitrary_types_allowed = True
        validate_assignment = True

    def to_yaml(self) -> str:
        """
        Export contract model to YAML format.

        Returns:
            str: YAML representation of the contract
        """
        from omnibase_core.utils.safe_yaml_loader import (
            serialize_pydantic_model_to_yaml,
        )

        return serialize_pydantic_model_to_yaml(
            self,
            default_flow_style=False,
            sort_keys=False,
        )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelContractGateway":
        """
        Create contract model from YAML content with proper enum handling.

        Args:
            yaml_content: YAML string representation

        Returns:
            ModelContractGateway: Validated contract model instance
        """
        from pydantic import ValidationError

        from omnibase_core.utils.safe_yaml_loader import load_yaml_content_as_model

        try:
            # Use safe YAML loader to parse content and validate as model
            return load_yaml_content_as_model(yaml_content, cls)

        except ValidationError as e:
            raise ValueError(f"Contract validation failed: {e}") from e
