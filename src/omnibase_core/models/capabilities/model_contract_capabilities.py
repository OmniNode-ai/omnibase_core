"""
Contract-derived capabilities model for capability-based auto-discovery.

This module provides the ModelContractCapabilities model that enables
capability-based auto-discovery and registration for ONEX nodes. It extends
the node capabilities system with contract-based metadata.

OMN-1124: ModelContractCapabilities - Contract-derived capabilities.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelContractCapabilities(BaseModel):
    """
    Contract-derived capabilities for capability-based auto-discovery.

    This model contains capabilities information derived from node contracts,
    enabling automatic discovery and registration of nodes based on their
    declared capabilities, supported intents, and implemented protocols.

    Use Cases:
    - Auto-discovery: Find nodes capable of handling specific intent types
    - Service registration: Register nodes with their contract metadata
    - Capability matching: Match requests to appropriate handler nodes
    - Protocol validation: Verify node implements required protocols

    Example:
        capabilities = ModelContractCapabilities(
            contract_type="orchestrator",
            contract_version=ModelSemVer(major=2, minor=0, patch=0),
            intent_types=["OrderCreated", "PaymentProcessed"],
            protocols=["ProtocolOrchestrator", "ProtocolWorkflowReducer"],
            capability_tags=["async", "distributed"],
            service_metadata={"environment": "production"},
        )

    Note:
        - from_attributes=True allows Pydantic to accept objects with matching
          attributes even when class identity differs (e.g., in pytest-xdist
          parallel execution where model classes are imported in separate workers).
        - See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    """

    # from_attributes=True allows Pydantic to accept objects with matching
    # attributes even when class identity differs (e.g., in pytest-xdist
    # parallel execution where model classes are imported in separate workers).
    # See CLAUDE.md section "Pydantic from_attributes=True for Value Objects".
    model_config = ConfigDict(extra="forbid", frozen=True, from_attributes=True)

    # ==========================================================================
    # Required Fields
    # ==========================================================================

    contract_type: str = Field(
        description="The type of contract (effect, compute, reducer, orchestrator)",
    )

    contract_version: ModelSemVer = Field(
        description="Semantic version of the contract specification",
    )

    # ==========================================================================
    # Optional List Fields (default to empty lists)
    # ==========================================================================

    intent_types: list[str] = Field(
        default_factory=list,
        description="Intent types this node handles for capability-based routing",
    )

    protocols: list[str] = Field(
        default_factory=list,
        description="Protocol interfaces this node implements",
    )

    capability_tags: list[str] = Field(
        default_factory=list,
        description="Tags for capability-based discovery and filtering",
    )

    # ==========================================================================
    # Optional Metadata Field
    # ==========================================================================

    service_metadata: dict[str, object] | None = Field(
        default=None,
        description="Optional service-level metadata for deployment and configuration",
    )


__all__ = ["ModelContractCapabilities"]
