# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Handler models for ONEX framework.

This module provides models for handler-related functionality including
artifact references, identifiers, packaging metadata references, security
metadata references, handler descriptors, and other handler configuration types.

Key Models:
    - ModelHandlerDescriptor: Canonical runtime representation of a handler
    - ModelIdentifier: Structured namespace:name identifier
    - ModelArtifactRef: Opaque artifact reference for registry resolution
    - ModelSecurityMetadataRef: Security configuration reference
    - ModelPackagingMetadataRef: Packaging configuration reference
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
