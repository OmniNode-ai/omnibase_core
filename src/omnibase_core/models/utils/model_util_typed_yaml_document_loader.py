# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed YAML document boundaries that preserve YAML null."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.errors.model_onex_error import ModelOnexError


def load_typed_yaml_document[T: BaseModel](path: Path, model_cls: type[T]) -> T | None:
    """Read ``path`` as UTF-8 YAML and validate present content with ``model_cls``.

    A blank, comment-only, or YAML-null document has no document value and returns
    ``None``. An empty mapping is present content and is passed to Pydantic so the
    supplied model determines whether it is valid.

    Raises:
        ModelOnexError: For unreadable input, malformed YAML, or model validation
            failures (including ``TypeError`` and ``ValueError`` raised by a
            validator). Unexpected validator ``RuntimeError`` values are wrapped
            as internal boundary failures. The original exception remains the cause.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ModelOnexError(
            message=f"YAML document not found: {path}",
            error_code=EnumCoreErrorCode.NOT_FOUND,
            operation="load_typed_yaml_document",
            source=str(path),
        ) from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise ModelOnexError(
            message=f"Unable to read YAML document: {path}",
            error_code=EnumCoreErrorCode.FILE_READ_ERROR,
            operation="load_typed_yaml_document",
            source=str(path),
        ) from exc

    return load_typed_yaml_content_document(content, model_cls, source=str(path))


def load_typed_yaml_content_document[T: BaseModel](
    content: str,
    model_cls: type[T],
    *,
    source: str | None = None,
) -> T | None:
    """Validate YAML text at a named source without normalizing YAML null to ``{}``.

    ``source`` identifies an in-memory, package-resource, or Git-backed document in
    structured failures without retaining its potentially sensitive content.
    """
    source_label = source if source is not None else "<YAML content>"

    try:
        document = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ModelOnexError(
            message=f"Unable to parse YAML document: {source_label}",
            error_code=EnumCoreErrorCode.CONVERSION_ERROR,
            operation="load_typed_yaml_content_document",
            source=source_label,
        ) from exc

    if document is None:
        return None

    try:
        return model_cls.model_validate(document)
    except VALIDATION_ERRORS as exc:
        raise ModelOnexError(
            message=f"YAML document validation failed: {source_label}",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            operation="load_typed_yaml_content_document",
            source=source_label,
        ) from exc
    except RuntimeError as exc:
        raise ModelOnexError(
            message=f"YAML document validation raised an internal error: {source_label}",
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            operation="load_typed_yaml_content_document",
            source=source_label,
        ) from exc
