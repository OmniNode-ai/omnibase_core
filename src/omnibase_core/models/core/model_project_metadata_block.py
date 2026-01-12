from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import SerializedDict

"""
Project metadata block model.
"""

from omnibase_core.enums.enum_metadata import EnumLifecycle, EnumMetaType
from omnibase_core.models.core.model_entrypoint import EntrypointBlock
from omnibase_core.models.core.model_onex_version import ModelOnexVersionInfo
from omnibase_core.models.core.model_tool_collection import ModelToolCollection
from omnibase_core.models.examples.model_tree_generator_config import (
    ModelTreeGeneratorConfig,
)
from omnibase_core.models.metadata.model_metadata_constants import (
    COPYRIGHT_KEY,
    ENTRYPOINT_KEY,
    METADATA_VERSION_KEY,
    PROJECT_ONEX_YAML_FILENAME,
    PROTOCOL_VERSION_KEY,
    SCHEMA_VERSION_KEY,
    TOOLS_KEY,
)
from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    parse_semver_from_string,
)


class ModelProjectMetadataBlock(BaseModel):
    """
    Canonical ONEX project-level metadata block.
    - tools: ModelToolCollection (not dict[str, Any])
    - meta_type: EnumMetaType (not str)
    - lifecycle: EnumLifecycle (not str)
    Entrypoint field must use the canonical URI format: '<type>://<target>'
    Example: 'python://main.py', 'yaml://project.onex.yaml', 'markdown://debug_log.md'
    """

    author: str
    name: str
    namespace: str
    description: str | None = None
    versions: ModelOnexVersionInfo
    lifecycle: EnumLifecycle = Field(default=EnumLifecycle.ACTIVE)
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
    meta_type: EnumMetaType = Field(default=EnumMetaType.PROJECT)
    tools: ModelToolCollection | None = None
    copyright: str
    tree_generator: ModelTreeGeneratorConfig | None = None
    # Add project-specific fields as needed

    model_config = ConfigDict(extra="allow")

    @classmethod
    def _parse_entrypoint(cls, value: object) -> str:
        # Accept EntrypointBlock or URI string, always return URI string
        if isinstance(value, str) and "://" in value:
            return value
        if hasattr(value, "type") and hasattr(value, "target"):
            return f"{value.type}://{value.target}"
        msg = f"Entrypoint must be a URI string or EntrypointBlock, got: {value}"
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=msg,
        )

    @classmethod
    def from_dict(cls, data: SerializedDict) -> "ModelProjectMetadataBlock":
        """Create a ModelProjectMetadataBlock from a dictionary.

        This factory method converts raw dictionary data (typically from YAML/JSON)
        into a fully validated ModelProjectMetadataBlock instance.

        Note:
            This method does NOT mutate the input dictionary. A defensive
            copy is made before any modifications to preserve caller's data.

        Args:
            data: Dictionary containing project metadata fields.

        Returns:
            Validated ModelProjectMetadataBlock instance.

        Raises:
            ModelOnexError: If required fields are missing or invalid.
        """
        # Make a defensive copy with proper type for mutations
        # Use dict[str, object] to allow assigning Pydantic model instances
        mutable_data: dict[str, object] = dict(data)

        # Convert entrypoint to EntrypointBlock if needed
        if ENTRYPOINT_KEY in mutable_data:
            entrypoint_val = mutable_data[ENTRYPOINT_KEY]
            if isinstance(entrypoint_val, str):
                mutable_data[ENTRYPOINT_KEY] = EntrypointBlock.from_uri(entrypoint_val)
            elif not isinstance(entrypoint_val, EntrypointBlock):
                msg = f"entrypoint must be a URI string or EntrypointBlock, got: {entrypoint_val}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )
        # Convert tools to ModelToolCollection if needed
        if TOOLS_KEY in mutable_data and isinstance(mutable_data[TOOLS_KEY], dict):
            mutable_data[TOOLS_KEY] = ModelToolCollection(tools=mutable_data[TOOLS_KEY])
        # Convert version fields to ModelOnexVersionInfo
        version_fields = [
            METADATA_VERSION_KEY,
            PROTOCOL_VERSION_KEY,
            SCHEMA_VERSION_KEY,
        ]
        if all(f in mutable_data for f in version_fields):
            # Convert version strings to ModelSemVer objects
            def _to_semver(val: object) -> ModelSemVer:
                """Convert version value to ModelSemVer."""
                if isinstance(val, ModelSemVer):
                    return val
                if isinstance(val, str):
                    return parse_semver_from_string(val)
                if isinstance(val, dict):
                    return ModelSemVer.model_validate(val)
                msg = f"Invalid version format: {val}"
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=msg,
                )

            mutable_data["versions"] = ModelOnexVersionInfo(
                metadata_version=_to_semver(mutable_data.pop(METADATA_VERSION_KEY)),
                protocol_version=_to_semver(mutable_data.pop(PROTOCOL_VERSION_KEY)),
                schema_version=_to_semver(mutable_data.pop(SCHEMA_VERSION_KEY)),
            )
        if COPYRIGHT_KEY not in mutable_data:
            msg = f"Missing required field: {COPYRIGHT_KEY}"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return cls.model_validate(mutable_data)

    def to_serializable_dict(self) -> SerializedDict:
        # Always emit entrypoint as URI string
        d = self.model_dump(exclude_none=True)
        d[ENTRYPOINT_KEY] = self._parse_entrypoint(self.entrypoint)
        # Omit empty/null/empty-string fields except protocol-required
        for k in list(d.keys()):
            if d[k] in (None, "", [], {}) and k not in {TOOLS_KEY}:
                d.pop(k)
        return d
