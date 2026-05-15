# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from omnibase_core.models.overlay.model_overlay_file import ModelOverlayFile


@pytest.mark.unit
class TestModelOverlayFile:
    def test_valid_overlay_round_trips(self) -> None:
        data = {
            "overlay_version": "1.0.0",
            "environment": "dev",
            "scope": "env",
            "transports": {
                "database": {
                    "POSTGRES_HOST": "192.168.86.201",
                    "POSTGRES_PORT": "5436",
                },
            },
        }
        overlay = ModelOverlayFile.model_validate(data)
        assert str(overlay.overlay_version) == "1.0.0"
        assert overlay.scope.value == "env"
        assert overlay.transports["database"]["POSTGRES_HOST"] == "192.168.86.201"

    def test_missing_overlay_version_fails(self) -> None:
        with pytest.raises(ValidationError):
            ModelOverlayFile.model_validate({"environment": "dev", "scope": "env"})

    def test_unsupported_version_rejected_at_model_level(self) -> None:
        with pytest.raises(ValidationError, match="overlay_version"):
            ModelOverlayFile.model_validate(
                {
                    "overlay_version": "99.0.0",
                    "environment": "dev",
                    "scope": "env",
                }
            )

    def test_invalid_scope_fails(self) -> None:
        with pytest.raises(ValidationError):
            ModelOverlayFile.model_validate(
                {
                    "overlay_version": "1.0.0",
                    "environment": "dev",
                    "scope": "invalid_scope",
                }
            )

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelOverlayFile.model_validate(
                {
                    "overlay_version": "1.0.0",
                    "environment": "dev",
                    "scope": "env",
                    "unknown_field": "value",
                }
            )

    def test_empty_transports_valid(self) -> None:
        overlay = ModelOverlayFile.model_validate(
            {
                "overlay_version": "1.0.0",
                "environment": "dev",
                "scope": "env",
            }
        )
        assert overlay.transports == {}

    def test_frozen_immutable(self) -> None:
        overlay = ModelOverlayFile.model_validate(
            {
                "overlay_version": "1.0.0",
                "environment": "dev",
                "scope": "env",
            }
        )
        with pytest.raises(ValidationError):
            overlay.environment = "prod"  # type: ignore[misc]

    def test_content_hash_deterministic(self) -> None:
        data = {
            "overlay_version": "1.0.0",
            "environment": "dev",
            "scope": "env",
            "transports": {"database": {"POSTGRES_HOST": "localhost"}},
        }
        a = ModelOverlayFile.model_validate(data)
        b = ModelOverlayFile.model_validate(data)
        assert a.content_hash() == b.content_hash()

    def test_content_hash_stable_across_key_order(self) -> None:
        data_a = {
            "overlay_version": "1.0.0",
            "environment": "dev",
            "scope": "env",
            "transports": {"database": {"B_KEY": "2", "A_KEY": "1"}},
        }
        data_b = {
            "overlay_version": "1.0.0",
            "environment": "dev",
            "scope": "env",
            "transports": {"database": {"A_KEY": "1", "B_KEY": "2"}},
        }
        a = ModelOverlayFile.model_validate(data_a)
        b = ModelOverlayFile.model_validate(data_b)
        assert a.content_hash() == b.content_hash()

    def test_all_env_pairs_collects_from_all_sections(self) -> None:
        overlay = ModelOverlayFile.model_validate(
            {
                "overlay_version": "1.0.0",
                "environment": "dev",
                "scope": "env",
                "transports": {"database": {"POSTGRES_HOST": "h"}},
                "secrets": {"INFISICAL_ADDR": "http://x"},
                "services": {"svc": {"ENABLE_POSTGRES": "true"}},
                "llm": {"coder": {"url": "http://y"}},
            }
        )
        pairs = overlay.all_env_pairs()
        assert pairs["POSTGRES_HOST"] == "h"
        assert pairs["INFISICAL_ADDR"] == "http://x"
        assert pairs["ENABLE_POSTGRES"] == "true"
        assert pairs["url"] == "http://y"

    def test_all_env_pairs_duplicate_key_same_value_accepted(self) -> None:
        overlay = ModelOverlayFile.model_validate(
            {
                "overlay_version": "1.0.0",
                "environment": "dev",
                "scope": "env",
                "transports": {"database": {"MY_KEY": "same"}},
                "secrets": {"MY_KEY": "same"},
            }
        )
        pairs = overlay.all_env_pairs()
        assert pairs["MY_KEY"] == "same"

    def test_all_env_pairs_duplicate_key_different_value_raises(self) -> None:
        overlay = ModelOverlayFile.model_validate(
            {
                "overlay_version": "1.0.0",
                "environment": "dev",
                "scope": "env",
                "transports": {"database": {"MY_KEY": "value1"}},
                "secrets": {"MY_KEY": "value2"},
            }
        )
        with pytest.raises(ValueError, match="MY_KEY"):
            overlay.all_env_pairs()

    def test_redacted_dump_masks_secret_keys(self) -> None:
        overlay = ModelOverlayFile.model_validate(
            {
                "overlay_version": "1.0.0",
                "environment": "dev",
                "scope": "env",
                "secrets": {"INFISICAL_CLIENT_SECRET": "actual_secret"},
                "transports": {"database": {"POSTGRES_PASSWORD": "db_pass"}},
            }
        )
        redacted = overlay.redacted_dump()
        assert redacted["secrets"]["INFISICAL_CLIENT_SECRET"] == "***REDACTED***"
        assert (
            redacted["transports"]["database"]["POSTGRES_PASSWORD"] == "***REDACTED***"
        )
