# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the typed YAML document file boundary."""

from pathlib import Path

import pytest
import yaml
from pydantic import BaseModel, ConfigDict, RootModel, ValidationError, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.utils.model_util_typed_yaml_document_loader import (
    load_typed_yaml_content_document,
    load_typed_yaml_document,
)
from omnibase_core.types.type_json import StrictJsonType


class _ModelExampleDocument(BaseModel):
    """Small strict schema used to test validation at the shared boundary."""

    model_config = ConfigDict(extra="forbid")

    name: str
    count: int


class _ModelMappingDocument(RootModel[dict[str, StrictJsonType]]):
    """Mapping-root schema used to distinguish an empty mapping from YAML null."""


class _ModelTypeErrorDocument(BaseModel):
    """Schema whose validator exercises Pydantic's unwrapped TypeError path."""

    name: str

    @field_validator("name")
    @classmethod
    def _raise_type_error(cls, value: str) -> str:
        raise TypeError(f"unsupported name: {value}")


class _ModelRuntimeErrorDocument(BaseModel):
    """Schema whose validator exercises an unexpected internal failure path."""

    name: str

    @field_validator("name")
    @classmethod
    def _raise_runtime_error(cls, value: str) -> str:
        raise RuntimeError(f"validator fault: {value}")


@pytest.mark.unit
@pytest.mark.parametrize("content", ["", "# comment-only document\n", "null\n"])
def test_load_typed_yaml_document_returns_none_for_absent_document(
    tmp_path: Path,
    content: str,
) -> None:
    """Blank, comment-only, and null YAML represent absence rather than ``{}``."""
    path = tmp_path / "document.yaml"
    path.write_text(content, encoding="utf-8")

    assert load_typed_yaml_document(path, _ModelMappingDocument) is None


@pytest.mark.unit
def test_load_typed_yaml_content_document_preserves_source_context() -> None:
    """Content-backed callers retain their source label without file I/O."""
    document = load_typed_yaml_content_document(
        "name: example\ncount: 2\n",
        _ModelExampleDocument,
        source="git:base:contracts/example.yaml",
    )

    assert document == _ModelExampleDocument(name="example", count=2)


@pytest.mark.unit
@pytest.mark.parametrize("content", ["", "# comment-only document\n", "null\n"])
def test_load_typed_yaml_content_document_returns_none_for_absent_document(
    content: str,
) -> None:
    """Content callers receive absence distinctly from an empty mapping."""
    assert load_typed_yaml_content_document(content, _ModelMappingDocument) is None


@pytest.mark.unit
def test_load_typed_yaml_content_document_wraps_malformed_yaml_with_source() -> None:
    """Content parsing failures retain a caller-provided source label and cause."""
    source = "git:base:contracts/example.yaml"

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_content_document(
            "name: [\n",
            _ModelExampleDocument,
            source=source,
        )

    assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR
    assert isinstance(exc_info.value.__cause__, yaml.YAMLError)
    assert source in exc_info.value.message
    assert exc_info.value.context["additional_context"]["source"] == source


@pytest.mark.unit
def test_load_typed_yaml_content_document_wraps_schema_failure_with_source() -> None:
    """Content validation failures retain a caller-provided source label and cause."""
    source = "package:omnibase_core/contracts/example.yaml"

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_content_document(
            "name: example\nunknown: value\n",
            _ModelExampleDocument,
            source=source,
        )

    assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert isinstance(exc_info.value.__cause__, ValidationError)
    assert source in exc_info.value.message
    assert exc_info.value.context["additional_context"]["source"] == source


@pytest.mark.unit
def test_load_typed_yaml_content_document_wraps_type_error_from_validator() -> None:
    """Pydantic's unwrapped TypeError remains a structured validation failure."""
    source = "package:omnibase_core/contracts/type-error.yaml"

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_content_document(
            "name: example\n",
            _ModelTypeErrorDocument,
            source=source,
        )

    assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert isinstance(exc_info.value.__cause__, TypeError)
    assert source in exc_info.value.message
    assert exc_info.value.context["additional_context"]["source"] == source


@pytest.mark.unit
def test_load_typed_yaml_content_document_wraps_runtime_error_from_validator() -> None:
    """Unexpected validator failures preserve the legacy loader's internal taxonomy."""
    source = "package:omnibase_core/contracts/runtime-error.yaml"

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_content_document(
            "name: example\n",
            _ModelRuntimeErrorDocument,
            source=source,
        )

    assert exc_info.value.error_code == EnumCoreErrorCode.INTERNAL_ERROR
    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert source in exc_info.value.message
    assert exc_info.value.context["additional_context"]["source"] == source


@pytest.mark.unit
def test_load_typed_yaml_document_wraps_missing_path(tmp_path: Path) -> None:
    """A missing path retains the established structured not-found taxonomy."""
    path = tmp_path / "missing.yaml"

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_document(path, _ModelExampleDocument)

    assert exc_info.value.error_code == EnumCoreErrorCode.NOT_FOUND
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)
    assert str(path) in exc_info.value.message


@pytest.mark.unit
def test_load_typed_yaml_document_validates_present_empty_mapping(
    tmp_path: Path,
) -> None:
    """An empty mapping is present content and validates as a mapping-root model."""
    path = tmp_path / "document.yaml"
    path.write_text("{}\n", encoding="utf-8")

    document = load_typed_yaml_document(path, _ModelMappingDocument)

    assert document is not None
    assert document.root == {}


@pytest.mark.unit
def test_load_typed_yaml_document_validates_typed_mapping(tmp_path: Path) -> None:
    """A present mapping is passed intact to the supplied Pydantic model."""
    path = tmp_path / "document.yaml"
    path.write_text("name: example\ncount: 2\n", encoding="utf-8")

    document = load_typed_yaml_document(path, _ModelExampleDocument)

    assert document == _ModelExampleDocument(name="example", count=2)


@pytest.mark.unit
def test_load_typed_yaml_document_wraps_malformed_yaml(tmp_path: Path) -> None:
    """Malformed YAML remains a structured conversion failure with its cause."""
    path = tmp_path / "document.yaml"
    path.write_text("name: [\n", encoding="utf-8")

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_document(path, _ModelExampleDocument)

    assert exc_info.value.error_code == EnumCoreErrorCode.CONVERSION_ERROR
    assert isinstance(exc_info.value.__cause__, yaml.YAMLError)
    assert str(path) in exc_info.value.message


@pytest.mark.unit
def test_load_typed_yaml_document_wraps_schema_failure(tmp_path: Path) -> None:
    """A present but invalid mapping remains a structured validation failure."""
    path = tmp_path / "document.yaml"
    path.write_text("name: example\nunknown: value\n", encoding="utf-8")

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_document(path, _ModelExampleDocument)

    assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
    assert isinstance(exc_info.value.__cause__, ValidationError)
    assert str(path) in exc_info.value.message


@pytest.mark.unit
def test_load_typed_yaml_document_wraps_invalid_utf8(tmp_path: Path) -> None:
    """Invalid UTF-8 is an explicit file-read failure rather than a YAML value."""
    path = tmp_path / "document.yaml"
    path.write_bytes(b"\xff")

    with pytest.raises(ModelOnexError) as exc_info:
        load_typed_yaml_document(path, _ModelExampleDocument)

    assert exc_info.value.error_code == EnumCoreErrorCode.FILE_READ_ERROR
    assert isinstance(exc_info.value.__cause__, UnicodeDecodeError)
    assert str(path) in exc_info.value.message
