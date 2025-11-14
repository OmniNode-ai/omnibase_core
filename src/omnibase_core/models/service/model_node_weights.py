from typing import Any, Self
from uuid import UUID

from pydantic import Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

"\nModelNodeWeights - Node weight configuration for load balancing\n\nNode weights model for configuring relative traffic distribution weights\nacross multiple nodes in a load balancing system.\n"
from pydantic import BaseModel


class ModelNodeWeights(BaseModel):
    """
    Node weight configuration for load balancing

    This model defines relative weights for distributing traffic across
    multiple nodes, with normalization and validation capabilities.
    """

    weights: dict[UUID, float] = Field(
        default_factory=dict, description="Node identifier to weight mapping"
    )
    default_weight: float = Field(
        default=1.0,
        description="Default weight for nodes not explicitly configured",
        ge=0.0,
        le=100.0,
    )
    auto_normalize: bool = Field(
        default=True,
        description="Whether to automatically normalize weights to sum to 1.0",
    )
    min_weight: float = Field(
        default=0.0, description="Minimum allowed weight value", ge=0.0
    )
    max_weight: float = Field(
        default=100.0, description="Maximum allowed weight value", ge=0.0
    )

    @model_validator(mode="after")
    def validate_weights(self) -> Self:
        """Ensure all weights are within valid range"""
        for node_id, weight in self.weights.items():
            if weight < self.min_weight:
                msg = f"Weight for {node_id} ({weight}) is below minimum ({self.min_weight})"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
                )
            if weight > self.max_weight:
                msg = f"Weight for {node_id} ({weight}) exceeds maximum ({self.max_weight})"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
                )
        return self

    def get_weight(self, node_id: UUID) -> float:
        """Get weight for a specific node, using default if not configured"""
        return self.weights.get(node_id, self.default_weight)

    def set_weight(self, node_id: UUID, weight: float) -> None:
        """Set weight for a specific node with validation"""
        if weight < self.min_weight:
            msg = f"Weight ({weight}) is below minimum ({self.min_weight})"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        if weight > self.max_weight:
            msg = f"Weight ({weight}) exceeds maximum ({self.max_weight})"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR, message=msg
            )
        self.weights[node_id] = weight

    def remove_weight(self, node_id: UUID) -> None:
        """Remove weight configuration for a node (will use default)"""
        self.weights.pop(node_id, None)

    def get_all_nodes(self) -> list[UUID]:
        """Get list of all configured node IDs"""
        return list(self.weights.keys())

    def get_total_weight(self) -> float:
        """Get sum of all configured weights"""
        return sum(self.weights.values())

    def normalize(self) -> "ModelNodeWeights":
        """Return normalized weights (sum to 1.0)"""
        total = self.get_total_weight()
        if total == 0:
            return self
        normalized_weights = {k: v / total for k, v in self.weights.items()}
        return ModelNodeWeights(
            weights=normalized_weights,
            default_weight=(
                self.default_weight / total if total > 0 else self.default_weight
            ),
            auto_normalize=self.auto_normalize,
            min_weight=self.min_weight,
            max_weight=self.max_weight,
        )

    def get_normalized_weight(self, node_id: UUID) -> float:
        """Get normalized weight for a specific node"""
        if self.auto_normalize:
            normalized = self.normalize()
            return normalized.get_weight(node_id)
        return self.get_weight(node_id)

    def get_weight_distribution(self) -> dict[UUID, float]:
        """Get weight distribution for all configured nodes"""
        if self.auto_normalize:
            normalized = self.normalize()
            return normalized.weights.copy()
        return self.weights.copy()

    def is_balanced(self, tolerance: float = 0.1) -> bool:
        """Check if weights are roughly balanced (within tolerance)"""
        if not self.weights:
            return True
        weights = list(self.weights.values())
        avg_weight = sum(weights) / len(weights)
        for weight in weights:
            if abs(weight - avg_weight) / avg_weight > tolerance:
                return False
        return True

    def get_effective_weights(self, active_nodes: list[UUID]) -> dict[UUID, float]:
        """Get effective weights for a subset of active nodes"""
        effective = {}
        for node_id in active_nodes:
            effective[node_id] = self.get_weight(node_id)
        if self.auto_normalize:
            total = sum(effective.values())
            if total > 0:
                effective = {k: v / total for k, v in effective.items()}
        return effective

    @classmethod
    def create_equal_weights(
        cls, node_ids: list[UUID], weight: float = 1.0
    ) -> "ModelNodeWeights":
        """Create equal weights for all specified nodes"""
        weights = dict[UUID, Any].fromkeys(node_ids, weight)
        return cls(weights=weights, auto_normalize=True)

    @classmethod
    def create_priority_weights(
        cls, node_priorities: dict[UUID, int]
    ) -> "ModelNodeWeights":
        """Create weights based on node priorities (higher priority = higher weight)"""
        max_priority = max(node_priorities.values()) if node_priorities else 1
        weights = {}
        for node_id, priority in node_priorities.items():
            weight = 1.0 + (priority - 1) * (9.0 / max(1, max_priority - 1))
            weights[node_id] = weight
        return cls(weights=weights, auto_normalize=True)

    @classmethod
    def create_capacity_weights(
        cls, node_capacities: dict[UUID, float]
    ) -> "ModelNodeWeights":
        """Create weights based on node capacities"""
        return cls(weights=node_capacities.copy(), auto_normalize=True)

    @classmethod
    def create_custom_weights(
        cls, node_weights: dict[UUID, float], normalize: bool = True
    ) -> "ModelNodeWeights":
        """Create custom weight configuration"""
        return cls(weights=node_weights.copy(), auto_normalize=normalize)
