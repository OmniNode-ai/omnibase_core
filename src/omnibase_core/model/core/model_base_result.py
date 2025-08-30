# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.872639'
# description: Stamped by ToolPython
# entrypoint: python://model_base_result
# hash: 56ff7bb25d511bb88e30e1a5428d893aa07412717203aa1ca79cb344ed618022
# last_modified_at: '2025-05-29T14:13:58.741391+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_base_result.py
# namespace: python://omnibase.model.model_base_result
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 78b1c43e-97d5-44da-a533-2e1a0f24a884
# version: 1.0.0
# === /OmniNode:Metadata ===


from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .model_base_error import ModelBaseError
from .model_generic_metadata import ModelGenericMetadata


class ModelBaseResult(BaseModel):
    exit_code: int
    success: bool
    errors: List[ModelBaseError] = Field(default_factory=list)
    metadata: Optional[ModelGenericMetadata] = (
        None  # Typed metadata with backward compatibility
    )

    def dict(self, **kwargs) -> Dict[str, Any]:
        """Override dict to maintain backward compatibility for metadata field."""
        result = super().dict(**kwargs)
        if self.metadata and isinstance(self.metadata, ModelGenericMetadata):
            result["metadata"] = self.metadata.to_dict()
        return result

    @classmethod
    def parse_obj(cls, obj: Any) -> "ModelBaseResult":
        """Override parse_obj to handle metadata conversion."""
        if isinstance(obj, dict) and "metadata" in obj and obj["metadata"] is not None:
            if not isinstance(obj["metadata"], ModelGenericMetadata):
                obj["metadata"] = ModelGenericMetadata.from_dict(obj["metadata"])
        return super().parse_obj(obj)
