# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Handler models for ONEX framework.

This module provides models for handler-related functionality including
artifact references, identifiers, packaging metadata references, security
metadata references, handler descriptors, and other handler configuration types.

Key Models
----------
ModelHandlerDescriptor
    Canonical runtime representation of a handler. Contains all metadata
    necessary for handler discovery, instantiation, routing, and lifecycle
    management. This is the authoritative runtime object produced by parsing
    handler contracts (YAML/JSON).

ModelIdentifier
    Structured identifier following the ``namespace:name[@variant]`` pattern.
    Used as the primary key for handler registry lookup and discovery.
    Immutable and hashable for use as dict keys.

ModelArtifactRef
    Opaque artifact reference for registry-resolved instantiation.
    Enables decoupled artifact management without inline content.

ModelSecurityMetadataRef
    Reference to security metadata configuration (allowed domains,
    secret scopes, classification level, access control policies).

ModelPackagingMetadataRef
    Reference to packaging metadata configuration (dependencies,
    entry points, distribution metadata).

Example Usage
-------------
Creating a handler descriptor:

    >>> from omnibase_core.models.handlers import (
    ...     ModelHandlerDescriptor,
    ...     ModelIdentifier,
    ... )
    >>> from omnibase_core.enums import (
    ...     EnumHandlerRole,
    ...     EnumHandlerType,
    ...     EnumHandlerTypeCategory,
    ... )
    >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
    >>>
    >>> descriptor = ModelHandlerDescriptor(
    ...     handler_name=ModelIdentifier(namespace="onex", name="validator"),
    ...     handler_version=ModelSemVer(major=1, minor=0, patch=0),
    ...     handler_role=EnumHandlerRole.COMPUTE_HANDLER,
    ...     handler_type=EnumHandlerType.NAMED,
    ...     handler_type_category=EnumHandlerTypeCategory.COMPUTE,
    ...     import_path="mypackage.handlers.Validator",
    ... )

Working with identifiers:

    >>> from omnibase_core.models.handlers import ModelIdentifier
    >>>
    >>> # Create from fields
    >>> id1 = ModelIdentifier(namespace="onex", name="compute")
    >>> str(id1)
    'onex:compute'
    >>>
    >>> # Parse from string
    >>> id2 = ModelIdentifier.parse("vendor:handler@v2")
    >>> id2.variant
    'v2'
    >>>
    >>> # Use as dict keys
    >>> cache = {id1: "cached_value"}
    >>> id1 in cache
    True

Thread Safety
-------------
All models in this module are immutable (frozen=True) after creation,
making them thread-safe for concurrent read access from multiple threads
or async tasks.

See Also
--------
omnibase_core.enums.enum_handler_role : Handler role classification
omnibase_core.enums.enum_handler_type : Handler type classification
omnibase_core.enums.enum_handler_type_category : Behavioral classification
omnibase_core.enums.enum_handler_capability : Handler capabilities

.. versionadded:: 0.4.0
"""

from omnibase_core.models.handlers.model_artifact_ref import ModelArtifactRef
from omnibase_core.models.handlers.model_handler_descriptor import (
    ModelHandlerDescriptor,
)
from omnibase_core.models.handlers.model_identifier import ModelIdentifier
from omnibase_core.models.handlers.model_packaging_metadata_ref import (
    ModelPackagingMetadataRef,
)
from omnibase_core.models.handlers.model_security_metadata_ref import (
    ModelSecurityMetadataRef,
)

__all__ = [
    "ModelArtifactRef",
    "ModelHandlerDescriptor",
    "ModelIdentifier",
    "ModelPackagingMetadataRef",
    "ModelSecurityMetadataRef",
]
