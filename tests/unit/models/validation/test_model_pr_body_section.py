# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelPrBodySection (OMN-14187)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.validation.model_pr_body_section import ModelPrBodySection


@pytest.mark.unit
class TestModelPrBodySection:
    def test_leading_unheaded_segment(self) -> None:
        section = ModelPrBodySection(heading=None, content="intro text")
        assert section.heading is None
        assert section.content == "intro text"
        assert section.is_stamp_section is False

    def test_headed_segment(self) -> None:
        section = ModelPrBodySection(heading="---", content="## Evidence\n")
        assert section.heading == "---"
        assert section.content == "## Evidence\n"

    def test_defaults(self) -> None:
        section = ModelPrBodySection()
        assert section.heading is None
        assert section.content == ""
        assert section.is_stamp_section is False

    def test_content_preserved_byte_for_byte(self) -> None:
        raw = "  leading spaces\n\ttab-indented\nline with trailing space   \n\n"
        section = ModelPrBodySection(content=raw)
        # Round-trip fidelity is the entire point of this model.
        assert section.content == raw
        restored = ModelPrBodySection.model_validate(section.model_dump())
        assert restored.content == raw

    def test_is_stamp_section_flag(self) -> None:
        section = ModelPrBodySection(
            heading="Evidence-Source",
            content="Evidence-Source: OCC#7\n",
            is_stamp_section=True,
        )
        assert section.is_stamp_section is True

    def test_serialization_roundtrip(self) -> None:
        section = ModelPrBodySection(
            heading="## Summary", content="body", is_stamp_section=False
        )
        assert ModelPrBodySection.model_validate(section.model_dump()) == section
        assert (
            ModelPrBodySection.model_validate_json(section.model_dump_json()) == section
        )

    def test_frozen_attribute_mutation_raises(self) -> None:
        section = ModelPrBodySection(content="x")
        with pytest.raises(ValidationError):
            section.content = "y"  # type: ignore[misc]

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ModelPrBodySection(content="x", order=1)  # type: ignore[call-arg]

    def test_to_json_deterministic(self) -> None:
        section = ModelPrBodySection(heading="h", content="c")
        assert section.to_json() == section.to_json()
