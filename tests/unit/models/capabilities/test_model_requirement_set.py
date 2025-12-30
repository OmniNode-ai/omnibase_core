# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ModelRequirementSet."""

import pytest
from pydantic import ValidationError

from omnibase_core.models.capabilities.model_requirement_set import ModelRequirementSet


@pytest.mark.unit
class TestModelRequirementSetInstantiation:
    """Tests for ModelRequirementSet instantiation."""

    def test_default_instantiation_creates_empty_requirements(self) -> None:
        """Test that default instantiation creates empty dicts."""
        reqs = ModelRequirementSet()
        assert reqs.must == {}
        assert reqs.prefer == {}
        assert reqs.forbid == {}
        assert reqs.hints == {}

    def test_instantiation_with_must_only(self) -> None:
        """Test creating requirements with only must constraints."""
        reqs = ModelRequirementSet(must={"key": "value"})
        assert reqs.must == {"key": "value"}
        assert reqs.prefer == {}
        assert reqs.forbid == {}
        assert reqs.hints == {}

    def test_instantiation_with_all_tiers(self) -> None:
        """Test creating requirements with all constraint tiers."""
        reqs = ModelRequirementSet(
            must={"required": True},
            prefer={"fast": True},
            forbid={"deprecated": True},
            hints={"vendor": ["a", "b"]},
        )
        assert reqs.must == {"required": True}
        assert reqs.prefer == {"fast": True}
        assert reqs.forbid == {"deprecated": True}
        assert reqs.hints == {"vendor": ["a", "b"]}

    def test_instantiation_with_complex_values(self) -> None:
        """Test creating requirements with complex nested values."""
        reqs = ModelRequirementSet(
            must={"features": ["tx", "encryption"], "version": {"min": 14}},
            prefer={"latency": {"max_ms": 20, "p99_ms": 50}},
        )
        assert reqs.must["features"] == ["tx", "encryption"]
        assert reqs.must["version"]["min"] == 14
        assert reqs.prefer["latency"]["max_ms"] == 20


@pytest.mark.unit
class TestModelRequirementSetProperties:
    """Tests for ModelRequirementSet properties."""

    def test_is_empty_true_for_default(self) -> None:
        """Test is_empty returns True for default requirements."""
        assert ModelRequirementSet().is_empty is True

    def test_is_empty_false_with_must(self) -> None:
        """Test is_empty returns False when must is populated."""
        reqs = ModelRequirementSet(must={"key": "value"})
        assert reqs.is_empty is False

    def test_is_empty_false_with_prefer(self) -> None:
        """Test is_empty returns False when prefer is populated."""
        reqs = ModelRequirementSet(prefer={"key": "value"})
        assert reqs.is_empty is False

    def test_is_empty_false_with_forbid(self) -> None:
        """Test is_empty returns False when forbid is populated."""
        reqs = ModelRequirementSet(forbid={"key": "value"})
        assert reqs.is_empty is False

    def test_is_empty_false_with_hints(self) -> None:
        """Test is_empty returns False when hints is populated."""
        reqs = ModelRequirementSet(hints={"key": "value"})
        assert reqs.is_empty is False

    def test_has_hard_constraints_false_for_empty(self) -> None:
        """Test has_hard_constraints returns False when empty."""
        assert ModelRequirementSet().has_hard_constraints is False

    def test_has_hard_constraints_true_with_must(self) -> None:
        """Test has_hard_constraints returns True with must."""
        reqs = ModelRequirementSet(must={"key": "value"})
        assert reqs.has_hard_constraints is True

    def test_has_hard_constraints_true_with_forbid(self) -> None:
        """Test has_hard_constraints returns True with forbid."""
        reqs = ModelRequirementSet(forbid={"key": "value"})
        assert reqs.has_hard_constraints is True

    def test_has_hard_constraints_false_with_only_soft(self) -> None:
        """Test has_hard_constraints returns False with only prefer/hints."""
        reqs = ModelRequirementSet(prefer={"a": 1}, hints={"b": 2})
        assert reqs.has_hard_constraints is False

    def test_has_soft_constraints_false_for_empty(self) -> None:
        """Test has_soft_constraints returns False when empty."""
        assert ModelRequirementSet().has_soft_constraints is False

    def test_has_soft_constraints_true_with_prefer(self) -> None:
        """Test has_soft_constraints returns True with prefer."""
        reqs = ModelRequirementSet(prefer={"key": "value"})
        assert reqs.has_soft_constraints is True

    def test_has_soft_constraints_true_with_hints(self) -> None:
        """Test has_soft_constraints returns True with hints."""
        reqs = ModelRequirementSet(hints={"key": "value"})
        assert reqs.has_soft_constraints is True

    def test_has_soft_constraints_false_with_only_hard(self) -> None:
        """Test has_soft_constraints returns False with only must/forbid."""
        reqs = ModelRequirementSet(must={"a": 1}, forbid={"b": 2})
        assert reqs.has_soft_constraints is False


@pytest.mark.unit
class TestModelRequirementSetMerge:
    """Tests for ModelRequirementSet.merge() method."""

    def test_merge_empty_with_empty(self) -> None:
        """Test merging two empty requirement sets."""
        a = ModelRequirementSet()
        b = ModelRequirementSet()
        merged = a.merge(b)
        assert merged.is_empty

    def test_merge_adds_new_keys(self) -> None:
        """Test merge adds keys from other."""
        a = ModelRequirementSet(must={"a": 1})
        b = ModelRequirementSet(must={"b": 2})
        merged = a.merge(b)
        assert merged.must == {"a": 1, "b": 2}

    def test_merge_other_takes_precedence(self) -> None:
        """Test merge uses other's values for conflicts."""
        a = ModelRequirementSet(must={"key": "original"})
        b = ModelRequirementSet(must={"key": "override"})
        merged = a.merge(b)
        assert merged.must == {"key": "override"}

    def test_merge_all_tiers(self) -> None:
        """Test merge works across all tiers."""
        a = ModelRequirementSet(
            must={"a": 1},
            prefer={"b": 2},
            forbid={"c": 3},
            hints={"d": 4},
        )
        b = ModelRequirementSet(
            must={"e": 5},
            prefer={"f": 6},
            forbid={"g": 7},
            hints={"h": 8},
        )
        merged = a.merge(b)
        assert merged.must == {"a": 1, "e": 5}
        assert merged.prefer == {"b": 2, "f": 6}
        assert merged.forbid == {"c": 3, "g": 7}
        assert merged.hints == {"d": 4, "h": 8}

    def test_merge_returns_new_instance(self) -> None:
        """Test merge returns new instance, doesn't modify originals."""
        a = ModelRequirementSet(must={"key": "a"})
        b = ModelRequirementSet(must={"key": "b"})
        merged = a.merge(b)
        assert a.must == {"key": "a"}  # Original unchanged
        assert b.must == {"key": "b"}  # Original unchanged
        assert merged.must == {"key": "b"}


@pytest.mark.unit
class TestModelRequirementSetImmutability:
    """Tests for ModelRequirementSet frozen immutability."""

    def test_frozen_immutability_must(self) -> None:
        """Test that must cannot be reassigned."""
        reqs = ModelRequirementSet(must={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.must = {"new": "dict"}  # type: ignore[misc]

    def test_frozen_immutability_prefer(self) -> None:
        """Test that prefer cannot be reassigned."""
        reqs = ModelRequirementSet(prefer={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.prefer = {"new": "dict"}  # type: ignore[misc]

    def test_frozen_immutability_forbid(self) -> None:
        """Test that forbid cannot be reassigned."""
        reqs = ModelRequirementSet(forbid={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.forbid = {"new": "dict"}  # type: ignore[misc]

    def test_frozen_immutability_hints(self) -> None:
        """Test that hints cannot be reassigned."""
        reqs = ModelRequirementSet(hints={"key": "value"})
        with pytest.raises(ValidationError, match="frozen"):
            reqs.hints = {"new": "dict"}  # type: ignore[misc]


@pytest.mark.unit
class TestModelRequirementSetExtraFields:
    """Tests for extra fields rejection."""

    def test_extra_fields_rejected(self) -> None:
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ModelRequirementSet(
                must={"key": "value"},
                extra_field="should_fail",  # type: ignore[call-arg]
            )


@pytest.mark.unit
class TestModelRequirementSetRepr:
    """Tests for ModelRequirementSet string representation."""

    def test_repr_empty(self) -> None:
        """Test repr for empty requirements."""
        reqs = ModelRequirementSet()
        assert repr(reqs) == "ModelRequirementSet()"

    def test_repr_with_must_only(self) -> None:
        """Test repr with only must."""
        reqs = ModelRequirementSet(must={"key": "value"})
        repr_str = repr(reqs)
        assert "ModelRequirementSet" in repr_str
        assert "must=" in repr_str
        assert "prefer=" not in repr_str

    def test_repr_with_all_tiers(self) -> None:
        """Test repr with all tiers."""
        reqs = ModelRequirementSet(
            must={"a": 1},
            prefer={"b": 2},
            forbid={"c": 3},
            hints={"d": 4},
        )
        repr_str = repr(reqs)
        assert "must=" in repr_str
        assert "prefer=" in repr_str
        assert "forbid=" in repr_str
        assert "hints=" in repr_str


@pytest.mark.unit
class TestModelRequirementSetEquality:
    """Tests for ModelRequirementSet equality (not hashable due to dict fields)."""

    def test_not_hashable_due_to_dict_fields(self) -> None:
        """Test that ModelRequirementSet is NOT hashable (contains dicts)."""
        reqs = ModelRequirementSet(must={"key": "value"})
        # Models with dict[str, Any] fields are frozen but not hashable
        with pytest.raises(TypeError, match="unhashable"):
            hash(reqs)

    def test_equality_same_requirements(self) -> None:
        """Test equality for identical requirements."""
        reqs1 = ModelRequirementSet(must={"a": 1}, prefer={"b": 2})
        reqs2 = ModelRequirementSet(must={"a": 1}, prefer={"b": 2})
        assert reqs1 == reqs2

    def test_inequality_different_requirements(self) -> None:
        """Test inequality for different requirements."""
        reqs1 = ModelRequirementSet(must={"a": 1})
        reqs2 = ModelRequirementSet(must={"a": 2})
        assert reqs1 != reqs2
