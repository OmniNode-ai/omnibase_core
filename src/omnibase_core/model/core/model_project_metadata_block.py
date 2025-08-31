"""
Project metadata block model.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_metadata import Lifecycle, MetaTypeEnum
from omnibase_core.metadata.metadata_constants import (
    COPYRIGHT_KEY,
    ENTRYPOINT_KEY,
    METADATA_VERSION_KEY,
    PROJECT_ONEX_YAML_FILENAME,
    PROTOCOL_VERSION_KEY,
    SCHEMA_VERSION_KEY,
    TOOLS_KEY,
)
from omnibase_core.model.core.model_entrypoint import EntrypointBlock
from omnibase_core.model.core.model_onex_version import ModelOnexVersionInfo
from omnibase_core.model.core.model_tool_collection import ModelToolCollection

from .model_tree_generator_config import ModelTreeGeneratorConfig


class ModelProjectMetadataBlock(BaseModel):
    """
    Canonical ONEX project-level metadata block.
    - tools: ModelToolCollection (not dict[str, Any])
    - meta_type: MetaTypeEnum (not str)
    - lifecycle: Lifecycle (not str)
    Entrypoint field must use the canonical URI format: '<type>://<target>'
    Example: 'python://main.py', 'yaml://project.onex.yaml', 'markdown://debug_log.md'
    """

    author: str
    name: str
    namespace: str
    description: str | None = None
    versions: ModelOnexVersionInfo
    lifecycle: Lifecycle = Field(default=Lifecycle.ACTIVE)
    created_at: str | None = None
    last_modified_at: str | None = None
    license: str | None = None
    # Entrypoint must be a URI: <type>://<target>
    entrypoint: EntrypointBlock = Field(
        default_factory=lambda: EntrypointBlock(
            type="yaml",
            target=PROJECT_ONEX_YAML_FILENAME,
        ),
    )
    meta_type: MetaTypeEnum = Field(default=MetaTypeEnum.PROJECT)
    tools: ModelToolCollection | None = None
    copyright: str
    tree_generator: ModelTreeGeneratorConfig | None = None
    # Add project-specific fields as needed

    model_config = {"extra": "allow"}

    @classmethod
    def _parse_entrypoint(cls, value) -> str:
        # Accept EntrypointBlock or URI string, always return URI string
        if isinstance(value, str) and "://" in value:
            return value
        if hasattr(value, "type") and hasattr(value, "target"):
            return f"{value.type}://{value.target}"
        msg = f"Entrypoint must be a URI string or EntrypointBlock, got: {value}"
        raise ValueError(
            msg,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ModelProjectMetadataBlock":
        # Convert entrypoint to EntrypointBlock if needed
        if ENTRYPOINT_KEY in data:
            entrypoint_val = data[ENTRYPOINT_KEY]
            if isinstance(entrypoint_val, str):
                data[ENTRYPOINT_KEY] = EntrypointBlock.from_uri(entrypoint_val)
            elif not isinstance(entrypoint_val, EntrypointBlock):
                msg = f"entrypoint must be a URI string or EntrypointBlock, got: {entrypoint_val}"
                raise ValueError(
                    msg,
                )
        # Convert tools to ModelToolCollection if needed
        if TOOLS_KEY in data and isinstance(data[TOOLS_KEY], dict):
            data[TOOLS_KEY] = ModelToolCollection(data[TOOLS_KEY])
        # Convert version fields to ModelOnexVersionInfo
        version_fields = [
            METADATA_VERSION_KEY,
            PROTOCOL_VERSION_KEY,
            SCHEMA_VERSION_KEY,
        ]
        if all(f in data for f in version_fields):
            data["versions"] = ModelOnexVersionInfo(
                metadata_version=data.pop(METADATA_VERSION_KEY),
                protocol_version=data.pop(PROTOCOL_VERSION_KEY),
                schema_version=data.pop(SCHEMA_VERSION_KEY),
            )
        if COPYRIGHT_KEY not in data:
            msg = f"Missing required field: {COPYRIGHT_KEY}"
            raise ValueError(msg)
        return cls(**data)

    def to_serializable_dict(self) -> dict:
        # Always emit entrypoint as URI string
        d = self.model_dump(exclude_none=True)
        d[ENTRYPOINT_KEY] = self._parse_entrypoint(self.entrypoint)
        # Omit empty/null/empty-string fields except protocol-required
        for k in list(d.keys()):
            if d[k] in (None, "", [], {}) and k not in {TOOLS_KEY}:
                d.pop(k)
        return d
