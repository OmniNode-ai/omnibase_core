# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Configuration Models

Models for system configuration, artifacts, and declarative settings.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.core.model_examples_collection import (
        ModelExamplesCollection,
    )
    from omnibase_core.models.examples.model_data_handling_declaration import (
        ModelDataHandlingDeclaration,
    )
    from omnibase_core.models.examples.model_example import ModelExample
    from omnibase_core.models.examples.model_example_metadata import (
        ModelExampleMetadata,
    )
    from omnibase_core.models.examples.model_fallback_strategy import (
        ModelFallbackStrategy,
    )

    from .model_artifact_type_config import ModelArtifactTypeConfig
    from .model_environment_properties import ModelEnvironmentProperties
    from .model_example_context_data import ModelExampleContextData
    from .model_example_data import ModelExampleInputData, ModelExampleOutputData
    from .model_example_metadata_summary import ModelExampleMetadataSummary
    from .model_example_summary import ModelExampleSummary
    from .model_examples_collection_summary import ModelExamplesCollectionSummary
    from .model_fallback_metadata import ModelFallbackMetadata
    from .model_namespace_config import ModelNamespaceConfig
    from .model_property_collection import ModelPropertyCollection
    from .model_property_metadata import ModelPropertyMetadata
    from .model_property_value import ModelPropertyValue
    from .model_typed_property import ModelTypedProperty
    from .model_uri import ModelOnexUri

__all__ = [
    "ModelArtifactTypeConfig",
    "ModelDataHandlingDeclaration",
    "ModelEnvironmentProperties",
    "ModelExample",
    "ModelExampleContextData",
    "ModelExampleInputData",
    "ModelExampleMetadata",
    "ModelExampleMetadataSummary",
    "ModelExampleOutputData",
    "ModelExampleSummary",
    "ModelExamplesCollection",
    "ModelExamplesCollectionSummary",
    "ModelFallbackMetadata",
    "ModelFallbackStrategy",
    "ModelNamespaceConfig",
    "ModelOnexUri",
    "ModelPropertyCollection",
    "ModelPropertyMetadata",
    "ModelPropertyValue",
    "ModelTypedProperty",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelExamplesCollection": (
        "omnibase_core.models.core.model_examples_collection",
        "ModelExamplesCollection",
    ),
    "ModelDataHandlingDeclaration": (
        "omnibase_core.models.examples.model_data_handling_declaration",
        "ModelDataHandlingDeclaration",
    ),
    "ModelExample": ("omnibase_core.models.examples.model_example", "ModelExample"),
    "ModelExampleMetadata": (
        "omnibase_core.models.examples.model_example_metadata",
        "ModelExampleMetadata",
    ),
    "ModelFallbackStrategy": (
        "omnibase_core.models.examples.model_fallback_strategy",
        "ModelFallbackStrategy",
    ),
    "ModelArtifactTypeConfig": (
        "omnibase_core.models.examples.model_artifact_type_config",
        "ModelArtifactTypeConfig",
    ),
    "ModelEnvironmentProperties": (
        "omnibase_core.models.examples.model_environment_properties",
        "ModelEnvironmentProperties",
    ),
    "ModelExampleContextData": (
        "omnibase_core.models.examples.model_example_context_data",
        "ModelExampleContextData",
    ),
    "ModelExampleInputData": (
        "omnibase_core.models.examples.model_example_data",
        "ModelExampleInputData",
    ),
    "ModelExampleOutputData": (
        "omnibase_core.models.examples.model_example_data",
        "ModelExampleOutputData",
    ),
    "ModelExampleMetadataSummary": (
        "omnibase_core.models.examples.model_example_metadata_summary",
        "ModelExampleMetadataSummary",
    ),
    "ModelExampleSummary": (
        "omnibase_core.models.examples.model_example_summary",
        "ModelExampleSummary",
    ),
    "ModelExamplesCollectionSummary": (
        "omnibase_core.models.examples.model_examples_collection_summary",
        "ModelExamplesCollectionSummary",
    ),
    "ModelFallbackMetadata": (
        "omnibase_core.models.examples.model_fallback_metadata",
        "ModelFallbackMetadata",
    ),
    "ModelNamespaceConfig": (
        "omnibase_core.models.examples.model_namespace_config",
        "ModelNamespaceConfig",
    ),
    "ModelPropertyCollection": (
        "omnibase_core.models.examples.model_property_collection",
        "ModelPropertyCollection",
    ),
    "ModelPropertyMetadata": (
        "omnibase_core.models.examples.model_property_metadata",
        "ModelPropertyMetadata",
    ),
    "ModelPropertyValue": (
        "omnibase_core.models.examples.model_property_value",
        "ModelPropertyValue",
    ),
    "ModelTypedProperty": (
        "omnibase_core.models.examples.model_typed_property",
        "ModelTypedProperty",
    ),
    "ModelOnexUri": ("omnibase_core.models.examples.model_uri", "ModelOnexUri"),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
