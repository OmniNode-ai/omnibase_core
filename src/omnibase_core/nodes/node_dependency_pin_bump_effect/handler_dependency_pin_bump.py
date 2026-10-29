# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Bump an opted-in consumer's omnibase-core dev tag (OMN-21478).

Run with ``python -m omnibase_core.nodes.node_dependency_pin_bump_effect.runtime_dependency_pin_bump``.
The workflow refreshes the consumer's lockfile after this handler succeeds.
"""

from __future__ import annotations

import re
import tomllib

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.handlers.handler_internal_sibling_pins_cli import load_contract
from omnibase_core.models.version_drift.model_dependency_pin_bump_request import (
    ModelDependencyPinBumpRequest,
)
from omnibase_core.models.version_drift.model_dependency_pin_bump_result import (
    ModelDependencyPinBumpResult,
)
from omnibase_core.models.version_drift.model_dependency_pin_manifest import (
    ModelDependencyPinManifest,
)
from omnibase_core.utils.util_safe_yaml_loader import load_yaml_content_as_model

__all__ = ["HandlerDependencyPinBump"]


class HandlerDependencyPinBump:
    """Rewrite only the declared git source tag, preserving the consumer's text."""

    def handle(
        self, request: ModelDependencyPinBumpRequest
    ) -> ModelDependencyPinBumpResult:
        """Return the changed pyproject path, or None for an unchanged pin."""
        manifest, repo = request.manifest, request.repo
        repo_root, dependency_tag = request.repo_root, request.dependency_tag
        settings = load_yaml_content_as_model(
            manifest.read_text("utf-8"), ModelDependencyPinManifest
        )
        entry = next((entry for entry in settings.repos if entry.name == repo), None)
        if entry is None:
            raise ModelOnexError(
                message=(f"repository {repo!r} is absent from {manifest}"),
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )
        if entry.dependency_pin is None:
            raise ModelOnexError(
                message=(f"repository {repo!r} has no declared dependency_pin"),
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )
        if re.fullmatch(load_contract().dev_tag_pattern, dependency_tag) is None:
            raise ModelOnexError(
                message=(f"dependency tag {dependency_tag!r} is not a dev merge tag"),
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )

        path = repo_root / entry.dependency_pin.pyproject
        content = path.read_bytes().decode("utf-8")
        document = tomllib.loads(content)
        try:
            source = document["tool"]["uv"]["sources"]["omnibase-core"]
        except (KeyError, TypeError) as exc:
            raise ModelOnexError(
                message=(f"{path}: missing omnibase-core git source"),
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            ) from exc
        if (
            not isinstance(source, dict)
            or not isinstance(source.get("git"), str)
            or source["git"].rstrip("/").removesuffix(".git").casefold()
            != "https://github.com/OmniNode-ai/omnibase_core".casefold()
            or not isinstance(source.get("tag"), str)
            or "rev" in source
            or "branch" in source
        ):
            raise ModelOnexError(
                message=(
                    f"{path}: omnibase-core must be a tagged git source of "
                    "https://github.com/OmniNode-ai/omnibase_core without rev or branch"
                ),
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )
        old_tag = source["tag"]
        if old_tag == dependency_tag:
            return ModelDependencyPinBumpResult()
        source["tag"] = dependency_tag
        for match in re.finditer(r"([\"'])(" + re.escape(old_tag) + r")\1", content):
            updated = (
                content[: match.start(2)] + dependency_tag + content[match.end(2) :]
            )
            try:
                matches_document = tomllib.loads(updated) == document
            except tomllib.TOMLDecodeError:
                continue
            if matches_document:
                path.write_bytes(updated.encode("utf-8"))
                return ModelDependencyPinBumpResult(changed_path=path)
        raise ModelOnexError(
            message=(f"{path}: cannot rewrite omnibase-core tag preserving TOML"),
            error_code=EnumCoreErrorCode.INVALID_INPUT,
        )
