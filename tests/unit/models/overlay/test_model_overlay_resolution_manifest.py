# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnibase_core.models.overlay.model_overlay_resolution_manifest import (
    ModelOverlayResolutionManifest,
)


@pytest.mark.unit
class TestModelOverlayResolutionManifest:
    def _make_manifest(self, **overrides: object) -> ModelOverlayResolutionManifest:
        defaults: dict[str, object] = {
            "overlay_file_hash": "sha256:abc123",
            "overlay_version": "1.0.0",
            "overlay_scope_stack": ("env",),
            "contract_requirements_hash": "sha256:def456",
            "resolved_config_hash": "sha256:789abc",
            "resolved_transports": ("database", "kafka"),
            "required_transports": ("database", "kafka", "valkey"),
            "runtime_version": "0.35.0",
            "timestamp": datetime.now(tz=UTC),
            "config_source": "overlay",
        }
        defaults.update(overrides)
        # NOTE(OMN-11070): mypy cannot statically verify the dynamically-built defaults dict matches the constructor signature
        return ModelOverlayResolutionManifest(**defaults)  # type: ignore[arg-type]

    def test_creates_with_all_fields(self) -> None:
        m = self._make_manifest()
        assert m.overlay_file_hash == "sha256:abc123"
        assert len(m.resolved_transports) == 2

    def test_frozen(self) -> None:
        m = self._make_manifest()
        with pytest.raises(ValidationError):
            # NOTE(OMN-11070): mypy flags assignment to frozen model field; ignore is intentional to test runtime enforcement
            m.runtime_version = "0.36.0"  # type: ignore[misc]

    def test_extra_forbidden(self) -> None:
        with pytest.raises((ValidationError, TypeError)):
            self._make_manifest(bogus_field="x")

    def test_stable_identity_hash_excludes_timestamp(self) -> None:
        t1 = datetime(2026, 1, 1, tzinfo=UTC)
        t2 = datetime(2026, 6, 1, tzinfo=UTC)
        m1 = self._make_manifest(timestamp=t1)
        m2 = self._make_manifest(timestamp=t2)
        assert m1.stable_identity_hash() == m2.stable_identity_hash()

    def test_stable_identity_hash_differs_on_content(self) -> None:
        m1 = self._make_manifest(resolved_config_hash="sha256:aaa")
        m2 = self._make_manifest(resolved_config_hash="sha256:bbb")
        assert m1.stable_identity_hash() != m2.stable_identity_hash()
