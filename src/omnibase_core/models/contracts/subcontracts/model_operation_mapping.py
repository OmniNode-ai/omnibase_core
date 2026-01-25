"""Operation mapping model for operation bindings DSL.

Combines an envelope template and optional response mapping for a single
operation. The operation name itself is the key in the parent mappings dict,
not a field on this model.

VERSION: 1.0.0

Author: ONEX Framework Team
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.contracts.subcontracts.model_envelope_template import (
    ModelEnvelopeTemplate,
)
from omnibase_core.models.contracts.subcontracts.model_response_mapping import (
    ModelResponseMapping,
)


class ModelOperationMapping(BaseModel):
    """
    Operation mapping combining envelope template and response mapping.

    This model defines a complete operation binding, specifying how to construct
    the handler envelope from request data and how to map the result back to
    response fields.

    The operation name (e.g., "store", "retrieve", "validate") is NOT a field
    on this model - it serves as the key in the parent mappings dictionary.

    Example YAML:
        .. code-block:: yaml

            mappings:
              store:  # <-- operation name is the dict key
                envelope:
                  operation: "write_file"
                  path: "${binding.config.base_path}/snapshots/${request.snapshot.snapshot_id}.json"
                  content: "${request.snapshot | to_json}"
                response:
                  status: "${result.status}"
                  snapshot: "${request.snapshot}"
                  error_message: "${result.error_message}"
                description: "Persist snapshot to filesystem"

              retrieve:  # <-- another operation
                envelope:
                  operation: "read_file"
                  path: "${binding.config.base_path}/snapshots/${request.snapshot_id}.json"
                response:
                  snapshot: "${result.content | from_json}"
                  error_message: "${result.error_message}"

    See Also:
        - ModelEnvelopeTemplate: Defines envelope construction with ${...} expressions
        - ModelResponseMapping: Defines result-to-response field mapping
        - ModelHandlerRoutingSubcontract: Uses operation mappings for handler routing
    """

    envelope: ModelEnvelopeTemplate = Field(
        ...,
        description="Template for constructing the handler envelope from request data",
    )

    response: ModelResponseMapping | None = Field(
        default=None,
        description="Optional mapping of handler result to response fields",
    )

    description: str | None = Field(
        default=None,
        description="Human-readable description of what this operation mapping does",
    )

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        has_response = self.response is not None
        return (
            f"ModelOperationMapping("
            f"envelope.operation={self.envelope.operation!r}, "
            f"has_response={has_response})"
        )


__all__ = ["ModelOperationMapping"]
