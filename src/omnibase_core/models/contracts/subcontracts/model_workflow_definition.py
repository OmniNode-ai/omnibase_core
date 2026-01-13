"""
Workflow Definition Model.

Model for complete workflow definitions in the ONEX workflow coordination system.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_coordination_rules import ModelCoordinationRules
from .model_execution_graph import ModelExecutionGraph
from .model_workflow_definition_metadata import ModelWorkflowDefinitionMetadata


class ModelWorkflowDefinition(BaseModel):
    """Complete workflow definition.

    v1.0.5 Reserved Fields Governance:
        Extra fields are allowed ("extra": "ignore") to support reserved fields
        for forward compatibility. Reserved fields (execution_graph, saga fields,
        compensation fields, etc.) are preserved during round-trip serialization
        but are NOT validated beyond structural type checking and MUST NOT
        influence any runtime decision in v1.0.
    """

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    workflow_metadata: ModelWorkflowDefinitionMetadata = Field(
        default=...,
        description="Workflow metadata",
    )

    execution_graph: ModelExecutionGraph = Field(
        default=...,
        description="Execution graph for the workflow",
    )

    coordination_rules: ModelCoordinationRules = Field(
        default_factory=lambda: ModelCoordinationRules(
            version=ModelSemVer(major=1, minor=0, patch=0)
        ),
        description="Rules for workflow coordination",
    )

    def compute_workflow_hash(self) -> str:
        """
        Compute SHA-256 hash of workflow definition for persistence and caching.

        Uses deterministic JSON serialization to ensure consistent hashes
        across different execution contexts. The hash is based on:
        - Workflow metadata (name, version, execution_mode, timeout)
        - Execution graph (nodes)
        - Coordination rules

        The hash excludes:
        - Runtime metadata (timestamps, UUIDs generated at runtime)
        - The workflow_hash field itself (to avoid circular dependency)

        Returns:
            Hex string of SHA-256 hash (64 characters)

        Example:
            Compute hash for workflow identification::

                workflow_def = ModelWorkflowDefinition(...)
                hash_value = workflow_def.compute_workflow_hash()
                # Store hash_value with contract for persistence/caching
        """
        # Create a dict excluding the workflow_hash field to avoid circular dependency
        workflow_dict = self.model_dump()

        # Remove workflow_hash from metadata if present (exclude from hash computation)
        if "workflow_metadata" in workflow_dict:
            workflow_dict["workflow_metadata"].pop("workflow_hash", None)

        # Serialize with sorted keys for deterministic output
        # Use default=str to handle UUIDs, datetimes, and other non-JSON types
        serialized = json.dumps(workflow_dict, sort_keys=True, default=str)

        # Compute SHA-256 hash
        return hashlib.sha256(serialized.encode()).hexdigest()

    def with_computed_hash(self) -> ModelWorkflowDefinition:
        """
        Return a new instance with workflow_hash computed and set in metadata.

        Creates a copy of this workflow definition with the workflow_hash
        field populated in workflow_metadata. This is useful for persistence
        and caching workflows before execution.

        Returns:
            New ModelWorkflowDefinition instance with workflow_hash set

        Example:
            Prepare workflow for persistence::

                workflow_def = ModelWorkflowDefinition(...)
                workflow_with_hash = workflow_def.with_computed_hash()
                # workflow_with_hash.workflow_metadata.workflow_hash is now set
                persist_workflow(workflow_with_hash)
        """
        computed_hash = self.compute_workflow_hash()

        # Create new metadata with the hash set
        new_metadata = self.workflow_metadata.model_copy(
            update={"workflow_hash": computed_hash}
        )

        # Return new workflow definition with updated metadata
        return self.model_copy(update={"workflow_metadata": new_metadata})
