# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for generated LLM reference constants (OMN-11932).

Covers LogicalModelKey and EndpointRef StrEnum values generated from
llm_endpoints.yaml and model_registry_v1.yaml.
"""

from __future__ import annotations

import pytest

from omnibase_core.constants.constants_llm_refs import EndpointRef, LogicalModelKey


@pytest.mark.unit
class TestLogicalModelKey:
    def test_all_registry_models_present(self) -> None:
        expected = {
            "qwen3-coder-30b",
            "deepseek-r1-14b",
            "deepseek-r1-32b",
            "qwen3-next-80b",
            "llama-3.3-70b-free",
            "claude-sonnet-4-6",
            "claude-opus-4-6",
        }
        actual = {m.value for m in LogicalModelKey}
        assert expected <= actual, f"Missing model keys: {expected - actual}"

    def test_values_are_strings(self) -> None:
        for key in LogicalModelKey:
            assert isinstance(key.value, str)

    def test_can_round_trip_from_string(self) -> None:
        for key in LogicalModelKey:
            assert LogicalModelKey(key.value) is key

    def test_known_model_key_by_attribute(self) -> None:
        assert LogicalModelKey.QWEN3_CODER_30B == "qwen3-coder-30b"
        assert LogicalModelKey.CLAUDE_SONNET_4_6 == "claude-sonnet-4-6"
        assert LogicalModelKey.CLAUDE_OPUS_4_6 == "claude-opus-4-6"

    def test_no_empty_values(self) -> None:
        for key in LogicalModelKey:
            assert key.value.strip(), f"Empty value for {key.name}"


@pytest.mark.unit
class TestEndpointRef:
    def test_all_running_slots_present(self) -> None:
        expected = {
            "coder-5090",
            "coder-fast-4090",
            "embeddings-201",
            "reasoning-deepseek-32b",
            "reasoning-moe-35b",
        }
        actual = {e.value for e in EndpointRef}
        assert expected <= actual, f"Missing endpoint refs: {expected - actual}"

    def test_values_are_strings(self) -> None:
        for ref in EndpointRef:
            assert isinstance(ref.value, str)

    def test_can_round_trip_from_string(self) -> None:
        for ref in EndpointRef:
            assert EndpointRef(ref.value) is ref

    def test_known_slot_by_attribute(self) -> None:
        assert EndpointRef.CODER_5090 == "coder-5090"
        assert EndpointRef.CODER_FAST_4090 == "coder-fast-4090"
        assert EndpointRef.EMBEDDINGS_201 == "embeddings-201"

    def test_no_empty_values(self) -> None:
        for ref in EndpointRef:
            assert ref.value.strip(), f"Empty value for {ref.name}"
