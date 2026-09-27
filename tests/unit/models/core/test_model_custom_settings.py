# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Wire-contract regressions for ``ModelCustomSettings.version``."""

from __future__ import annotations

import pytest

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_custom_settings import ModelCustomSettings
from omnibase_core.models.primitives.model_semver import ModelSemVer


@pytest.mark.unit
def test_version_absence_and_explicit_none_preserve_optional_contract() -> None:
    """The optional field must not invent a record version for absent wire data."""
    assert ModelCustomSettings().version is None
    assert ModelCustomSettings(version=None).version is None
    assert ModelCustomSettings.model_validate({"version": None}).version is None
    parsed_from_dict = ModelCustomSettings.from_dict({"version": None})
    assert parsed_from_dict is not None
    assert parsed_from_dict.version is None


@pytest.mark.unit
def test_version_accepts_typed_and_canonical_string_semver() -> None:
    """Typed and canonical wire SemVer inputs retain their declared meaning."""
    typed_version = ModelSemVer(major=2, minor=3, patch=4)
    assert ModelCustomSettings(version=typed_version).version == typed_version

    parsed = ModelCustomSettings.model_validate({"version": "2.3.4"})
    assert parsed.version == typed_version
    assert parsed.model_dump(mode="json")["version"] == {
        "major": 2,
        "minor": 3,
        "patch": 4,
        "prerelease": None,
        "build": None,
    }
    assert ModelCustomSettings.model_validate_json(
        parsed.model_dump_json()
    ).version == (typed_version)


@pytest.mark.unit
def test_version_rejects_malformed_string_through_canonical_parser() -> None:
    """Malformed wire versions fail closed rather than falling back to 1.0.0."""
    with pytest.raises(ModelOnexError, match="Invalid semantic version format"):
        ModelCustomSettings.model_validate({"version": "not-a-semver"})
