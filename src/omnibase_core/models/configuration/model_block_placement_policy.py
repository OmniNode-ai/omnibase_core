# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-28T13:24:07.883679'
# description: Stamped by ToolPython
# entrypoint: python://model_block_placement_policy
# hash: 08a9ed26e52ba33d3ddd85d75314c1d9cfc0a295608b3322e44492ad268c9c30
# last_modified_at: '2025-05-29T14:13:58.749316+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_block_placement_policy.py
# namespace: python://omnibase.model.model_block_placement_policy
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: 3cc55211-330d-4b36-a981-a7d958d08261
# version: 1.0.0
# === /OmniNode:Metadata ===


from pydantic import BaseModel, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelBlockPlacementPolicy(BaseModel):
    """
    Canonical policy for placement and normalization of ONEX metadata blocks in files.
    This model is the single source of truth for all block placement rules.
    """

    allow_shebang: bool = Field(
        default=True,
        description="Allow a shebang (#!...) at the very top of the file.",
    )
    max_blank_lines_before_block: int = Field(
        default=1,
        description="Maximum blank lines allowed before the metadata block (after shebang, if present).",
    )
    allow_license_header: bool = Field(
        default=False,
        description="Allow a license header above the metadata block.",
    )
    license_header_pattern: str | None = Field(
        default=None,
        description="Regex pattern for allowed license header lines.",
    )
    normalize_blank_lines: bool = Field(
        default=True,
        description="Normalize all blank lines above the block to at most one.",
    )
    enforce_block_at_top: bool = Field(
        default=True,
        description="Enforce that the metadata block is at the top (after shebang/license header, if allowed).",
    )
    placement_policy_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the placement policy.",
    )
