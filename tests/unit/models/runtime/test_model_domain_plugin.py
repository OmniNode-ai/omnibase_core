# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Tests for domain plugin runtime model compatibility imports."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_domain_plugin_result_importable_from_compat_module() -> None:
    """The SPI protocol imports both domain plugin models from one module."""
    from omnibase_core.models.runtime.model_domain_plugin import (
        ModelDomainPluginResult as CompatResult,
    )
    from omnibase_core.models.runtime.model_domain_plugin_result import (
        ModelDomainPluginResult as CanonicalResult,
    )

    assert CompatResult is CanonicalResult


def test_domain_plugin_result_importable_from_runtime_package() -> None:
    """Runtime package exports the result model for public consumers."""
    from omnibase_core.models.runtime import ModelDomainPluginResult as PackageResult
    from omnibase_core.models.runtime.model_domain_plugin_result import (
        ModelDomainPluginResult as CanonicalResult,
    )

    assert PackageResult is CanonicalResult
