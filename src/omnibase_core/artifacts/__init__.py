# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Content-addressed artifact storage and its canonical public API."""

from __future__ import annotations

from omnibase_core.artifacts.artifact_secret_detector import SecretDetector
from omnibase_core.artifacts.artifact_store import (
    ARTIFACT_STORE_ROOT_ENV,
    DEFAULT_READ_CHUNK_BYTES,
    RESTRICTED_ARTIFACT_KINDS,
    WRITER_VERSION,
    ArtifactStore,
)
from omnibase_core.errors.error_artifact_configuration import (
    ArtifactConfigurationError,
)
from omnibase_core.errors.error_artifact_integrity import ArtifactIntegrityError
from omnibase_core.errors.error_artifact_not_found import ArtifactNotFoundError
from omnibase_core.errors.error_artifact_quota_exceeded import (
    ArtifactQuotaExceededError,
)
from omnibase_core.errors.error_artifact_secret_detected import (
    ArtifactSecretDetectedError,
)
from omnibase_core.errors.error_artifact_unauthorized import (
    ArtifactUnauthorizedError,
)

__all__ = [
    "ARTIFACT_STORE_ROOT_ENV",
    "DEFAULT_READ_CHUNK_BYTES",
    "RESTRICTED_ARTIFACT_KINDS",
    "WRITER_VERSION",
    "ArtifactConfigurationError",
    "ArtifactIntegrityError",
    "ArtifactNotFoundError",
    "ArtifactQuotaExceededError",
    "ArtifactSecretDetectedError",
    "ArtifactStore",
    "ArtifactUnauthorizedError",
    "SecretDetector",
]
