# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Regression coverage for OMN-17617's version/generation DTO contracts."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import BaseModel, ValidationError

from omnibase_core.models.core.model_extracted_block import ModelExtractedBlock
from omnibase_core.models.core.model_file_reference import ModelFileReference
from omnibase_core.models.core.model_generated_file import ModelGeneratedFile
from omnibase_core.models.core.model_generated_models import ModelGeneratedModels
from omnibase_core.models.core.model_generation_result import ModelGenerationResult
from omnibase_core.models.core.model_mixin_version import ModelMixinVersion
from omnibase_core.models.core.model_multi_doc_generation_result import (
    ModelMultiDocGenerationResult,
)
from omnibase_core.models.core.model_node_template import ModelNodeTemplateConfig
from omnibase_core.models.core.model_node_version_constraints import (
    ModelNodeVersionConstraints,
)
from omnibase_core.models.core.model_onex_version import ModelOnexVersionInfo
from omnibase_core.models.core.model_parse_metadata import ModelParseMetadata
from omnibase_core.models.core.model_regeneration_target import ModelRegenerationTarget
from omnibase_core.models.core.model_rendered_template import ModelRenderedTemplate
from omnibase_core.models.core.model_template_context import ModelTemplateContext
from omnibase_core.models.core.model_version_deployment import ModelVersionDeployment
from omnibase_core.models.core.model_version_documentation import (
    ModelVersionDocumentation,
)
from omnibase_core.models.core.model_version_file import ModelVersionFile
from omnibase_core.models.core.model_version_implementation import (
    ModelVersionImplementation,
)
from omnibase_core.models.core.model_version_manifest_class import ModelVersionManifest
from omnibase_core.models.core.model_version_security import ModelVersionSecurity
from omnibase_core.models.core.model_version_status import ModelVersionStatus
from omnibase_core.models.core.model_version_testing import ModelVersionTesting
from omnibase_core.models.core.model_yaml_section import ModelYamlSection
from omnibase_core.models.primitives.model_semver import ModelSemVer

MODEL_FQNS: tuple[str, ...] = (
    "omnibase_core.models.core.model_extracted_block:ModelExtractedBlock",
    "omnibase_core.models.core.model_file_reference:ModelFileReference",
    "omnibase_core.models.core.model_generated_file:ModelGeneratedFile",
    "omnibase_core.models.core.model_generated_models:ModelGeneratedModels",
    "omnibase_core.models.core.model_generation_result:ModelGenerationResult",
    "omnibase_core.models.core.model_mixin_version:ModelMixinVersion",
    "omnibase_core.models.core.model_multi_doc_generation_result:ModelMultiDocGenerationResult",
    "omnibase_core.models.core.model_node_template:ModelNodeTemplateConfig",
    "omnibase_core.models.core.model_node_version_constraints:ModelNodeVersionConstraints",
    "omnibase_core.models.core.model_onex_version:ModelOnexVersionInfo",
    "omnibase_core.models.core.model_parse_metadata:ModelParseMetadata",
    "omnibase_core.models.core.model_regeneration_target:ModelRegenerationTarget",
    "omnibase_core.models.core.model_rendered_template:ModelRenderedTemplate",
    "omnibase_core.models.core.model_template_context:ModelTemplateContext",
    "omnibase_core.models.core.model_version_deployment:ModelVersionDeployment",
    "omnibase_core.models.core.model_version_documentation:ModelVersionDocumentation",
    "omnibase_core.models.core.model_version_file:ModelVersionFile",
    "omnibase_core.models.core.model_version_implementation:ModelVersionImplementation",
    "omnibase_core.models.core.model_version_manifest_class:ModelVersionManifest",
    "omnibase_core.models.core.model_version_security:ModelVersionSecurity",
    "omnibase_core.models.core.model_version_status:ModelVersionStatus",
    "omnibase_core.models.core.model_version_testing:ModelVersionTesting",
    "omnibase_core.models.core.model_yaml_section:ModelYamlSection",
)

_SEMVER: dict[str, object] = {"major": 1, "minor": 0, "patch": 0}
_FIXED_UUID = UUID("00000000-0000-4000-8000-000000000001")
_FIXED_TIME = datetime(2026, 1, 1, tzinfo=UTC)

MODEL_CASES: tuple[tuple[type[BaseModel], dict[str, object]], ...] = (
    (
        ModelExtractedBlock,
        {
            "metadata": {
                "uuid": _FIXED_UUID,
                "name": "test-node",
                "version": _SEMVER,
                "author": "OmniNode",
                "created_at": "2026-01-01T00:00:00Z",
                "last_modified_at": "2026-01-01T00:00:00Z",
                "hash": "a" * 64,
                "entrypoint": "python://main.py",
                "namespace": "onex.tools.test",
            },
            "body": "body",
        },
    ),
    (ModelFileReference, {"path": "contract.yaml"}),
    (
        ModelGeneratedFile,
        {"path": Path("node.py"), "content": "pass", "file_type": "python"},
    ),
    (ModelGeneratedModels, {}),
    (
        ModelGenerationResult,
        {
            "success": True,
            "files_generated": [],
            "files_modified": [],
            "errors": [],
            "warnings": [],
            "generation_time": _FIXED_TIME,
            "node_name": "example",
            "operation_type": "generate",
            "total_operations": 1,
        },
    ),
    (ModelMixinVersion, _SEMVER),
    (
        ModelMultiDocGenerationResult,
        {"contract_path": Path("contract.yaml"), "output_dir": Path("output")},
    ),
    (
        ModelNodeTemplateConfig,
        {
            "template_version": _SEMVER,
            "node_name": "example",
            "template_files": {},
            "generated_files": [],
        },
    ),
    (ModelNodeVersionConstraints, {}),
    (
        ModelOnexVersionInfo,
        {
            "metadata_version": _SEMVER,
            "protocol_version": _SEMVER,
            "schema_version": _SEMVER,
        },
    ),
    (
        ModelParseMetadata,
        {"source_command": "generate", "parser_version": _SEMVER},
    ),
    (ModelRegenerationTarget, {"path": Path("node.py")}),
    (ModelRenderedTemplate, {"content": "rendered"}),
    (
        ModelTemplateContext,
        {
            "node_name": "example",
            "node_class": "NodeExample",
            "node_id": _FIXED_UUID,
            "node_id_upper": _FIXED_UUID,
            "author": "OmniNode",
            "year": 2026,
            "version": _SEMVER,
        },
    ),
    (ModelVersionDeployment, {}),
    (ModelVersionDocumentation, {}),
    (
        ModelVersionFile,
        {
            "file_path": "node.py",
            "file_type": "python",
            "description": "generated node",
        },
    ),
    (
        ModelVersionImplementation,
        {"main_class_name": "NodeExample", "namespace": "omnibase.nodes"},
    ),
    (
        ModelVersionManifest,
        {
            "version": _SEMVER,
            "status": "active",
            "release_date": _FIXED_TIME,
            "contract": {
                "contract_version": _SEMVER,
                "contract_name": "example",
                "validation_status": "fully_compliant",
            },
            "implementation": {
                "main_class_name": "NodeExample",
                "namespace": "omnibase.nodes",
            },
            "testing": {},
            "deployment": {},
            "security": {},
            "documentation": {},
            "schema_version": _SEMVER,
            "blueprint_version": _SEMVER,
        },
    ),
    (ModelVersionSecurity, {}),
    (ModelVersionStatus, {}),
    (ModelVersionTesting, {}),
    (ModelYamlSection, {}),
)

MODEL_TYPES = tuple(model_type for model_type, _ in MODEL_CASES)


@pytest.mark.unit
def test_omn17617_inventory_is_explicitly_strict() -> None:
    """Every ticket-owned DTO rejects undeclared wire keys."""
    assert len(MODEL_FQNS) == len(MODEL_CASES) == 23
    assert (
        tuple(
            f"{model_type.__module__}:{model_type.__name__}"
            for model_type in MODEL_TYPES
        )
        == MODEL_FQNS
    )


@pytest.mark.unit
@pytest.mark.parametrize(("model_type", "payload"), MODEL_CASES)
def test_version_generation_wire_contracts_reject_unknown_and_round_trip(
    model_type: type[BaseModel], payload: dict[str, object]
) -> None:
    """Every ticket-owned DTO has a complete strict runtime wire contract."""
    with pytest.raises(ValidationError, match="unexpected"):
        model_type.model_validate({**payload, "unexpected": True})

    validated = model_type.model_validate(payload)
    assert model_type.model_validate_json(validated.model_dump_json()) == validated
    assert model_type.model_config.get("extra") == "forbid"
    assert model_type.model_json_schema()["additionalProperties"] is False


@pytest.mark.unit
def test_version_authorities_are_required_without_inference() -> None:
    """Distinct aggregate and template record versions retain their declared owners."""
    with pytest.raises(ValidationError, match="metadata_version"):
        ModelOnexVersionInfo.model_validate(
            {
                "protocol_version": {"major": 1, "minor": 0, "patch": 0},
                "schema_version": {"major": 1, "minor": 0, "patch": 0},
            }
        )
    with pytest.raises(ValidationError, match="version"):
        ModelTemplateContext.model_validate(
            {
                "node_name": "example",
                "node_class": "NodeExample",
                "node_id": _FIXED_UUID,
                "node_id_upper": _FIXED_UUID,
                "author": "OmniNode",
                "year": 2026,
            }
        )


@pytest.mark.unit
def test_parse_metadata_remains_mutable_after_strict_wire_validation() -> None:
    """Strict wire keys do not change the parser's explicit mutation lifecycle."""
    metadata = ModelParseMetadata(
        source_command="generate",
        parser_version=ModelSemVer(major=1, minor=0, patch=0),
    )

    metadata.add_debug_info("trace_id", "abc123")

    assert metadata.debug_info["trace_id"] == "abc123"
    assert ModelGeneratedFile(
        path=Path("node.py"), content="pass", file_type="python"
    ).path == Path("node.py")
