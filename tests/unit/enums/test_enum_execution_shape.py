# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for EnumMessageCategory and EnumExecutionShape.

Tests all aspects of the execution shape and message category enums including:
- Enum value validation
- Helper methods
- String representation
- Topic parsing and inference
- Target and source mappings
- Categorization logic
- Property-based tests for invariants
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from omnibase_core.enums.enum_execution_shape import (
    EnumExecutionShape,
    EnumMessageCategory,
)


@pytest.mark.unit
class TestEnumMessageCategory:
    """Test cases for EnumMessageCategory."""

    def test_enum_values_exist(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "EVENT": "event",
            "COMMAND": "command",
            "INTENT": "intent",
        }

        for name, value in expected_values.items():
            category = getattr(EnumMessageCategory, name)
            assert category.value == value

    def test_str_method_returns_correct_value(self):
        """Test __str__ method returns the value string."""
        assert str(EnumMessageCategory.EVENT) == "event"
        assert str(EnumMessageCategory.COMMAND) == "command"
        assert str(EnumMessageCategory.INTENT) == "intent"

    def test_topic_suffix_property(self):
        """Test topic_suffix property returns pluralized suffix."""
        assert EnumMessageCategory.EVENT.topic_suffix == "events"
        assert EnumMessageCategory.COMMAND.topic_suffix == "commands"
        assert EnumMessageCategory.INTENT.topic_suffix == "intents"

    def test_from_topic_simple_topics(self):
        """Test from_topic with simple topic patterns."""
        assert (
            EnumMessageCategory.from_topic("user.events") == EnumMessageCategory.EVENT
        )
        assert (
            EnumMessageCategory.from_topic("user.commands")
            == EnumMessageCategory.COMMAND
        )
        assert (
            EnumMessageCategory.from_topic("user.intents") == EnumMessageCategory.INTENT
        )

    def test_from_topic_versioned_topics(self):
        """Test from_topic with versioned topic patterns."""
        assert (
            EnumMessageCategory.from_topic("dev.user.events.v1")
            == EnumMessageCategory.EVENT
        )
        assert (
            EnumMessageCategory.from_topic("prod.order.commands.v2")
            == EnumMessageCategory.COMMAND
        )
        assert (
            EnumMessageCategory.from_topic("staging.workflow.intents.v3")
            == EnumMessageCategory.INTENT
        )

    def test_from_topic_complex_versioned_topics(self):
        """Test from_topic with complex multi-segment versioned topics."""
        assert (
            EnumMessageCategory.from_topic("dev.archon.user.events.v1")
            == EnumMessageCategory.EVENT
        )
        assert (
            EnumMessageCategory.from_topic("prod.domain.service.commands.v2")
            == EnumMessageCategory.COMMAND
        )

    def test_from_topic_case_insensitive(self):
        """Test from_topic handles case-insensitive matching."""
        assert (
            EnumMessageCategory.from_topic("USER.EVENTS") == EnumMessageCategory.EVENT
        )
        assert (
            EnumMessageCategory.from_topic("User.Commands")
            == EnumMessageCategory.COMMAND
        )
        assert (
            EnumMessageCategory.from_topic("user.INTENTS") == EnumMessageCategory.INTENT
        )

    def test_from_topic_invalid_topics_return_none(self):
        """Test from_topic returns None for invalid topics."""
        assert EnumMessageCategory.from_topic("invalid.topic") is None
        assert EnumMessageCategory.from_topic("user.data") is None
        assert EnumMessageCategory.from_topic("some.random.path") is None
        assert EnumMessageCategory.from_topic("") is None
        assert EnumMessageCategory.from_topic("events") is None  # No dot prefix
        assert EnumMessageCategory.from_topic("user.event") is None  # Singular

    def test_try_from_topic_success(self):
        """Test try_from_topic returns category and None error on success."""
        category, error = EnumMessageCategory.try_from_topic("user.events")
        assert category == EnumMessageCategory.EVENT
        assert error is None

        category, error = EnumMessageCategory.try_from_topic("dev.user.commands.v1")
        assert category == EnumMessageCategory.COMMAND
        assert error is None

        category, error = EnumMessageCategory.try_from_topic(
            "staging.workflow.intents.v2"
        )
        assert category == EnumMessageCategory.INTENT
        assert error is None

    def test_try_from_topic_case_insensitive(self):
        """Test try_from_topic handles case-insensitive matching."""
        category, error = EnumMessageCategory.try_from_topic("USER.EVENTS")
        assert category == EnumMessageCategory.EVENT
        assert error is None

        category, error = EnumMessageCategory.try_from_topic("User.Commands")
        assert category == EnumMessageCategory.COMMAND
        assert error is None

    def test_try_from_topic_failure_returns_error(self):
        """Test try_from_topic returns None and error message on failure."""
        category, error = EnumMessageCategory.try_from_topic("invalid.topic")
        assert category is None
        assert error is not None
        assert "No message category pattern found" in error
        assert "invalid.topic" in error

    def test_try_from_topic_empty_string(self):
        """Test try_from_topic handles empty string."""
        category, error = EnumMessageCategory.try_from_topic("")
        assert category is None
        assert error == "Empty topic string provided"

    def test_try_from_topic_whitespace_only(self):
        """Test try_from_topic handles whitespace-only string."""
        category, error = EnumMessageCategory.try_from_topic("   ")
        assert category is None
        assert error == "Topic string contains only whitespace"

    def test_is_fact_based(self):
        """Test is_fact_based method identifies EVENT as fact-based."""
        assert EnumMessageCategory.is_fact_based(EnumMessageCategory.EVENT) is True
        assert EnumMessageCategory.is_fact_based(EnumMessageCategory.COMMAND) is False
        assert EnumMessageCategory.is_fact_based(EnumMessageCategory.INTENT) is False

    def test_is_action_oriented(self):
        """Test is_action_oriented method identifies COMMAND and INTENT."""
        assert (
            EnumMessageCategory.is_action_oriented(EnumMessageCategory.EVENT) is False
        )
        assert (
            EnumMessageCategory.is_action_oriented(EnumMessageCategory.COMMAND) is True
        )
        assert (
            EnumMessageCategory.is_action_oriented(EnumMessageCategory.INTENT) is True
        )

    def test_is_goal_oriented(self):
        """Test is_goal_oriented method identifies only INTENT."""
        assert EnumMessageCategory.is_goal_oriented(EnumMessageCategory.EVENT) is False
        assert (
            EnumMessageCategory.is_goal_oriented(EnumMessageCategory.COMMAND) is False
        )
        assert EnumMessageCategory.is_goal_oriented(EnumMessageCategory.INTENT) is True

    def test_get_description(self):
        """Test get_description returns human-readable descriptions."""
        assert (
            EnumMessageCategory.get_description(EnumMessageCategory.EVENT)
            == "Something that happened (past-tense, immutable fact)"
        )
        assert (
            EnumMessageCategory.get_description(EnumMessageCategory.COMMAND)
            == "A request to do something (imperative action)"
        )
        assert (
            EnumMessageCategory.get_description(EnumMessageCategory.INTENT)
            == "A desire to achieve an outcome (goal-oriented)"
        )

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert EnumMessageCategory.EVENT == EnumMessageCategory.EVENT
        assert EnumMessageCategory.COMMAND != EnumMessageCategory.EVENT
        assert EnumMessageCategory.INTENT != EnumMessageCategory.COMMAND

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_categories = [
            EnumMessageCategory.EVENT,
            EnumMessageCategory.COMMAND,
            EnumMessageCategory.INTENT,
        ]

        for category in all_categories:
            assert category in EnumMessageCategory

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        categories = list(EnumMessageCategory)
        assert len(categories) == 3

        category_values = {cat.value for cat in categories}
        expected_values = {"event", "command", "intent"}

        assert category_values == expected_values


@pytest.mark.unit
class TestEnumExecutionShape:
    """Test cases for EnumExecutionShape."""

    def test_enum_values_exist(self):
        """Test that all expected enum values are present."""
        expected_values = {
            "EVENT_TO_ORCHESTRATOR": "event_to_orchestrator",
            "EVENT_TO_REDUCER": "event_to_reducer",
            "INTENT_TO_EFFECT": "intent_to_effect",
            "COMMAND_TO_ORCHESTRATOR": "command_to_orchestrator",
            "COMMAND_TO_EFFECT": "command_to_effect",
        }

        for name, value in expected_values.items():
            shape = getattr(EnumExecutionShape, name)
            assert shape.value == value

    def test_str_method_returns_correct_value(self):
        """Test __str__ method returns the value string."""
        assert str(EnumExecutionShape.EVENT_TO_ORCHESTRATOR) == "event_to_orchestrator"
        assert str(EnumExecutionShape.EVENT_TO_REDUCER) == "event_to_reducer"
        assert str(EnumExecutionShape.INTENT_TO_EFFECT) == "intent_to_effect"
        assert (
            str(EnumExecutionShape.COMMAND_TO_ORCHESTRATOR) == "command_to_orchestrator"
        )
        assert str(EnumExecutionShape.COMMAND_TO_EFFECT) == "command_to_effect"

    def test_get_source_category_for_all_shapes(self):
        """Test get_source_category returns correct category for all shapes."""
        # Event shapes
        assert (
            EnumExecutionShape.get_source_category(
                EnumExecutionShape.EVENT_TO_ORCHESTRATOR
            )
            == EnumMessageCategory.EVENT
        )
        assert (
            EnumExecutionShape.get_source_category(EnumExecutionShape.EVENT_TO_REDUCER)
            == EnumMessageCategory.EVENT
        )

        # Intent shapes
        assert (
            EnumExecutionShape.get_source_category(EnumExecutionShape.INTENT_TO_EFFECT)
            == EnumMessageCategory.INTENT
        )

        # Command shapes
        assert (
            EnumExecutionShape.get_source_category(
                EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
            )
            == EnumMessageCategory.COMMAND
        )
        assert (
            EnumExecutionShape.get_source_category(EnumExecutionShape.COMMAND_TO_EFFECT)
            == EnumMessageCategory.COMMAND
        )

    def test_get_target_node_kind_for_all_shapes(self):
        """Test get_target_node_kind returns correct target for all shapes."""
        assert (
            EnumExecutionShape.get_target_node_kind(
                EnumExecutionShape.EVENT_TO_ORCHESTRATOR
            )
            == "orchestrator"
        )
        assert (
            EnumExecutionShape.get_target_node_kind(EnumExecutionShape.EVENT_TO_REDUCER)
            == "reducer"
        )
        assert (
            EnumExecutionShape.get_target_node_kind(EnumExecutionShape.INTENT_TO_EFFECT)
            == "effect"
        )
        assert (
            EnumExecutionShape.get_target_node_kind(
                EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
            )
            == "orchestrator"
        )
        assert (
            EnumExecutionShape.get_target_node_kind(
                EnumExecutionShape.COMMAND_TO_EFFECT
            )
            == "effect"
        )

    def test_targets_coordinator(self):
        """Test targets_coordinator identifies orchestrator shapes."""
        # Shapes targeting orchestrator
        assert (
            EnumExecutionShape.targets_coordinator(
                EnumExecutionShape.EVENT_TO_ORCHESTRATOR
            )
            is True
        )
        assert (
            EnumExecutionShape.targets_coordinator(
                EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
            )
            is True
        )

        # Shapes not targeting orchestrator
        assert (
            EnumExecutionShape.targets_coordinator(EnumExecutionShape.EVENT_TO_REDUCER)
            is False
        )
        assert (
            EnumExecutionShape.targets_coordinator(EnumExecutionShape.INTENT_TO_EFFECT)
            is False
        )
        assert (
            EnumExecutionShape.targets_coordinator(EnumExecutionShape.COMMAND_TO_EFFECT)
            is False
        )

    def test_targets_effect(self):
        """Test targets_effect identifies effect shapes."""
        # Shapes targeting effect
        assert (
            EnumExecutionShape.targets_effect(EnumExecutionShape.INTENT_TO_EFFECT)
            is True
        )
        assert (
            EnumExecutionShape.targets_effect(EnumExecutionShape.COMMAND_TO_EFFECT)
            is True
        )

        # Shapes not targeting effect
        assert (
            EnumExecutionShape.targets_effect(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
            is False
        )
        assert (
            EnumExecutionShape.targets_effect(EnumExecutionShape.EVENT_TO_REDUCER)
            is False
        )
        assert (
            EnumExecutionShape.targets_effect(
                EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
            )
            is False
        )

    def test_targets_reducer(self):
        """Test targets_reducer identifies reducer shapes."""
        # Shapes targeting reducer
        assert (
            EnumExecutionShape.targets_reducer(EnumExecutionShape.EVENT_TO_REDUCER)
            is True
        )

        # Shapes not targeting reducer
        assert (
            EnumExecutionShape.targets_reducer(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
            is False
        )
        assert (
            EnumExecutionShape.targets_reducer(EnumExecutionShape.INTENT_TO_EFFECT)
            is False
        )
        assert (
            EnumExecutionShape.targets_reducer(
                EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
            )
            is False
        )
        assert (
            EnumExecutionShape.targets_reducer(EnumExecutionShape.COMMAND_TO_EFFECT)
            is False
        )

    def test_get_shapes_for_category_event(self):
        """Test get_shapes_for_category with EVENT category."""
        shapes = EnumExecutionShape.get_shapes_for_category(EnumMessageCategory.EVENT)
        assert len(shapes) == 2
        assert EnumExecutionShape.EVENT_TO_ORCHESTRATOR in shapes
        assert EnumExecutionShape.EVENT_TO_REDUCER in shapes

    def test_get_shapes_for_category_command(self):
        """Test get_shapes_for_category with COMMAND category."""
        shapes = EnumExecutionShape.get_shapes_for_category(EnumMessageCategory.COMMAND)
        assert len(shapes) == 2
        assert EnumExecutionShape.COMMAND_TO_ORCHESTRATOR in shapes
        assert EnumExecutionShape.COMMAND_TO_EFFECT in shapes

    def test_get_shapes_for_category_intent(self):
        """Test get_shapes_for_category with INTENT category."""
        shapes = EnumExecutionShape.get_shapes_for_category(EnumMessageCategory.INTENT)
        assert len(shapes) == 1
        assert EnumExecutionShape.INTENT_TO_EFFECT in shapes

    def test_get_shapes_for_target_orchestrator(self):
        """Test get_shapes_for_target with orchestrator target."""
        shapes = EnumExecutionShape.get_shapes_for_target("orchestrator")
        assert len(shapes) == 2
        assert EnumExecutionShape.EVENT_TO_ORCHESTRATOR in shapes
        assert EnumExecutionShape.COMMAND_TO_ORCHESTRATOR in shapes

    def test_get_shapes_for_target_effect(self):
        """Test get_shapes_for_target with effect target."""
        shapes = EnumExecutionShape.get_shapes_for_target("effect")
        assert len(shapes) == 2
        assert EnumExecutionShape.INTENT_TO_EFFECT in shapes
        assert EnumExecutionShape.COMMAND_TO_EFFECT in shapes

    def test_get_shapes_for_target_reducer(self):
        """Test get_shapes_for_target with reducer target."""
        shapes = EnumExecutionShape.get_shapes_for_target("reducer")
        assert len(shapes) == 1
        assert EnumExecutionShape.EVENT_TO_REDUCER in shapes

    def test_get_shapes_for_target_unknown(self):
        """Test get_shapes_for_target with unknown target returns empty list."""
        shapes = EnumExecutionShape.get_shapes_for_target("compute")
        assert len(shapes) == 0
        assert shapes == []

        shapes = EnumExecutionShape.get_shapes_for_target("invalid")
        assert len(shapes) == 0

    def test_get_description_for_all_shapes(self):
        """Test get_description returns human-readable descriptions for all shapes."""
        assert (
            EnumExecutionShape.get_description(EnumExecutionShape.EVENT_TO_ORCHESTRATOR)
            == "Events routed to orchestrators for workflow coordination"
        )
        assert (
            EnumExecutionShape.get_description(EnumExecutionShape.EVENT_TO_REDUCER)
            == "Events routed to reducers for state aggregation"
        )
        assert (
            EnumExecutionShape.get_description(EnumExecutionShape.INTENT_TO_EFFECT)
            == "Intents routed to effects for external actions"
        )
        assert (
            EnumExecutionShape.get_description(
                EnumExecutionShape.COMMAND_TO_ORCHESTRATOR
            )
            == "Commands routed to orchestrators for workflow execution"
        )
        assert (
            EnumExecutionShape.get_description(EnumExecutionShape.COMMAND_TO_EFFECT)
            == "Commands routed to effects for direct execution"
        )

    def test_enum_equality(self):
        """Test enum equality comparison."""
        assert (
            EnumExecutionShape.EVENT_TO_ORCHESTRATOR
            == EnumExecutionShape.EVENT_TO_ORCHESTRATOR
        )
        assert (
            EnumExecutionShape.EVENT_TO_REDUCER
            != EnumExecutionShape.EVENT_TO_ORCHESTRATOR
        )
        assert (
            EnumExecutionShape.INTENT_TO_EFFECT != EnumExecutionShape.COMMAND_TO_EFFECT
        )

    def test_enum_membership(self):
        """Test enum membership checking."""
        all_shapes = [
            EnumExecutionShape.EVENT_TO_ORCHESTRATOR,
            EnumExecutionShape.EVENT_TO_REDUCER,
            EnumExecutionShape.INTENT_TO_EFFECT,
            EnumExecutionShape.COMMAND_TO_ORCHESTRATOR,
            EnumExecutionShape.COMMAND_TO_EFFECT,
        ]

        for shape in all_shapes:
            assert shape in EnumExecutionShape

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        shapes = list(EnumExecutionShape)
        assert len(shapes) == 5

        shape_values = {s.value for s in shapes}
        expected_values = {
            "event_to_orchestrator",
            "event_to_reducer",
            "intent_to_effect",
            "command_to_orchestrator",
            "command_to_effect",
        }

        assert shape_values == expected_values

    def test_shape_source_and_target_consistency(self):
        """Test that all shapes have consistent source and target mappings."""
        for shape in EnumExecutionShape:
            # Every shape should have a valid source category
            source = EnumExecutionShape.get_source_category(shape)
            assert source in EnumMessageCategory

            # Every shape should have a valid target node kind
            target = EnumExecutionShape.get_target_node_kind(shape)
            assert target in {"orchestrator", "reducer", "effect"}

            # Target methods should be consistent with get_target_node_kind
            if target == "orchestrator":
                assert EnumExecutionShape.targets_coordinator(shape) is True
                assert EnumExecutionShape.targets_effect(shape) is False
                assert EnumExecutionShape.targets_reducer(shape) is False
            elif target == "effect":
                assert EnumExecutionShape.targets_coordinator(shape) is False
                assert EnumExecutionShape.targets_effect(shape) is True
                assert EnumExecutionShape.targets_reducer(shape) is False
            elif target == "reducer":
                assert EnumExecutionShape.targets_coordinator(shape) is False
                assert EnumExecutionShape.targets_effect(shape) is False
                assert EnumExecutionShape.targets_reducer(shape) is True


@pytest.mark.unit
class TestEnumMessageCategoryAndExecutionShapeIntegration:
    """Integration tests for EnumMessageCategory and EnumExecutionShape."""

    def test_all_categories_have_at_least_one_shape(self):
        """Test that every message category has at least one execution shape."""
        for category in EnumMessageCategory:
            shapes = EnumExecutionShape.get_shapes_for_category(category)
            assert len(shapes) >= 1, f"Category {category} has no execution shapes"

    def test_topic_to_shape_workflow(self):
        """Test the workflow from topic to possible execution shapes."""
        # Parse topic to category
        category = EnumMessageCategory.from_topic("dev.user.events.v1")
        assert category == EnumMessageCategory.EVENT

        # Get possible shapes for category
        shapes = EnumExecutionShape.get_shapes_for_category(category)
        assert len(shapes) == 2

        # Verify all shapes have EVENT as source
        for shape in shapes:
            assert (
                EnumExecutionShape.get_source_category(shape)
                == EnumMessageCategory.EVENT
            )

    def test_all_targets_have_at_least_one_shape(self):
        """Test that orchestrator, effect, and reducer all have shapes."""
        for target in ["orchestrator", "effect", "reducer"]:
            shapes = EnumExecutionShape.get_shapes_for_target(target)
            assert len(shapes) >= 1, f"Target {target} has no execution shapes"

    def test_shape_descriptions_are_non_empty(self):
        """Test that all shapes have non-empty descriptions."""
        for shape in EnumExecutionShape:
            description = EnumExecutionShape.get_description(shape)
            assert description, f"Shape {shape} has empty description"
            assert len(description) > 10, f"Shape {shape} has too short description"

    def test_category_descriptions_are_non_empty(self):
        """Test that all categories have non-empty descriptions."""
        for category in EnumMessageCategory:
            description = EnumMessageCategory.get_description(category)
            assert description, f"Category {category} has empty description"
            assert len(description) > 10, (
                f"Category {category} has too short description"
            )


@pytest.mark.unit
class TestPropertyBasedExecutionShapes:
    """Property-based tests for execution shapes using Hypothesis.

    These tests verify invariants that must hold for all enum values,
    providing stronger guarantees than example-based tests alone.
    """

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_all_shapes_have_valid_source_category(
        self, shape: EnumExecutionShape
    ) -> None:
        """Property: Every shape must have a valid source category."""
        source = EnumExecutionShape.get_source_category(shape)
        assert source in EnumMessageCategory
        assert isinstance(source, EnumMessageCategory)

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_all_shapes_have_valid_target(self, shape: EnumExecutionShape) -> None:
        """Property: Every shape must have a valid target node kind."""
        target = EnumExecutionShape.get_target_node_kind(shape)
        valid_targets = {"orchestrator", "reducer", "effect"}
        assert target in valid_targets, f"Shape {shape} has invalid target: {target}"

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_shape_string_round_trip(self, shape: EnumExecutionShape) -> None:
        """Property: Shape string serialization must round-trip correctly."""
        # Serialize to string
        shape_str = str(shape)
        # Verify it matches the value
        assert shape_str == shape.value
        # Verify we can reconstruct from value
        reconstructed = EnumExecutionShape(shape_str)
        assert reconstructed == shape

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_target_predicate_exclusivity(self, shape: EnumExecutionShape) -> None:
        """Property: Each shape targets exactly one node type."""
        targets_orch = EnumExecutionShape.targets_coordinator(shape)
        targets_eff = EnumExecutionShape.targets_effect(shape)
        targets_red = EnumExecutionShape.targets_reducer(shape)

        # Exactly one must be true
        target_count = sum([targets_orch, targets_eff, targets_red])
        assert target_count == 1, (
            f"Shape {shape} targets {target_count} node types, expected exactly 1"
        )

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_target_predicate_matches_target_kind(
        self, shape: EnumExecutionShape
    ) -> None:
        """Property: Target predicates must be consistent with get_target_node_kind."""
        target_kind = EnumExecutionShape.get_target_node_kind(shape)

        if target_kind == "orchestrator":
            assert EnumExecutionShape.targets_coordinator(shape) is True
            assert EnumExecutionShape.targets_effect(shape) is False
            assert EnumExecutionShape.targets_reducer(shape) is False
        elif target_kind == "effect":
            assert EnumExecutionShape.targets_coordinator(shape) is False
            assert EnumExecutionShape.targets_effect(shape) is True
            assert EnumExecutionShape.targets_reducer(shape) is False
        elif target_kind == "reducer":
            assert EnumExecutionShape.targets_coordinator(shape) is False
            assert EnumExecutionShape.targets_effect(shape) is False
            assert EnumExecutionShape.targets_reducer(shape) is True

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_shape_in_category_shapes(self, shape: EnumExecutionShape) -> None:
        """Property: Every shape appears in its source category's shape list."""
        source_category = EnumExecutionShape.get_source_category(shape)
        shapes_for_category = EnumExecutionShape.get_shapes_for_category(
            source_category
        )
        assert shape in shapes_for_category

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_shape_in_target_shapes(self, shape: EnumExecutionShape) -> None:
        """Property: Every shape appears in its target's shape list."""
        target_kind = EnumExecutionShape.get_target_node_kind(shape)
        shapes_for_target = EnumExecutionShape.get_shapes_for_target(target_kind)
        assert shape in shapes_for_target

    @given(st.sampled_from(list(EnumExecutionShape)))
    @settings(max_examples=50)
    def test_shape_has_non_empty_description(self, shape: EnumExecutionShape) -> None:
        """Property: Every shape must have a non-empty description."""
        description = EnumExecutionShape.get_description(shape)
        assert description is not None
        assert len(description) > 0
        assert description != "Unknown execution shape"


@pytest.mark.unit
class TestPropertyBasedMessageCategory:
    """Property-based tests for message categories using Hypothesis."""

    @given(st.sampled_from(list(EnumMessageCategory)))
    @settings(max_examples=50)
    def test_category_string_round_trip(self, category: EnumMessageCategory) -> None:
        """Property: Category string serialization must round-trip correctly."""
        # Serialize to string
        category_str = str(category)
        # Verify it matches the value
        assert category_str == category.value
        # Verify we can reconstruct from value
        reconstructed = EnumMessageCategory(category_str)
        assert reconstructed == category

    @given(st.sampled_from(list(EnumMessageCategory)))
    @settings(max_examples=50)
    def test_topic_suffix_round_trip(self, category: EnumMessageCategory) -> None:
        """Property: topic_suffix creates valid topic that parses back."""
        suffix = category.topic_suffix
        # Create a topic with the suffix
        topic = f"test.{suffix}"
        # Parse it back
        parsed = EnumMessageCategory.from_topic(topic)
        assert parsed == category

    @given(st.sampled_from(list(EnumMessageCategory)))
    @settings(max_examples=50)
    def test_versioned_topic_round_trip(self, category: EnumMessageCategory) -> None:
        """Property: Versioned topics parse correctly."""
        suffix = category.topic_suffix
        # Create a versioned topic
        topic = f"dev.domain.{suffix}.v1"
        # Parse it back
        parsed = EnumMessageCategory.from_topic(topic)
        assert parsed == category

    @given(st.sampled_from(list(EnumMessageCategory)))
    @settings(max_examples=50)
    def test_category_has_non_empty_description(
        self, category: EnumMessageCategory
    ) -> None:
        """Property: Every category must have a non-empty description."""
        description = EnumMessageCategory.get_description(category)
        assert description is not None
        assert len(description) > 0
        assert description != "Unknown message category"

    @given(st.sampled_from(list(EnumMessageCategory)))
    @settings(max_examples=50)
    def test_category_classification_consistency(
        self, category: EnumMessageCategory
    ) -> None:
        """Property: Classification methods must be logically consistent."""
        is_fact = EnumMessageCategory.is_fact_based(category)
        is_action = EnumMessageCategory.is_action_oriented(category)
        is_goal = EnumMessageCategory.is_goal_oriented(category)

        # EVENT is fact-based, not action-oriented, not goal-oriented
        if category == EnumMessageCategory.EVENT:
            assert is_fact is True
            assert is_action is False
            assert is_goal is False

        # COMMAND is action-oriented but not goal-oriented or fact-based
        if category == EnumMessageCategory.COMMAND:
            assert is_fact is False
            assert is_action is True
            assert is_goal is False

        # INTENT is goal-oriented and action-oriented but not fact-based
        if category == EnumMessageCategory.INTENT:
            assert is_fact is False
            assert is_action is True
            assert is_goal is True

    @given(st.sampled_from(list(EnumMessageCategory)))
    @settings(max_examples=50)
    def test_category_has_at_least_one_shape(
        self, category: EnumMessageCategory
    ) -> None:
        """Property: Every category must have at least one execution shape."""
        shapes = EnumExecutionShape.get_shapes_for_category(category)
        assert len(shapes) >= 1, f"Category {category} has no execution shapes"

    @given(st.sampled_from(list(EnumMessageCategory)))
    @settings(max_examples=50)
    def test_topic_suffix_is_pluralized_value(
        self, category: EnumMessageCategory
    ) -> None:
        """Property: Topic suffix must be pluralized form of value."""
        suffix = category.topic_suffix
        assert suffix == f"{category.value}s"


@pytest.mark.unit
class TestPropertyBasedCrossEnumInvariants:
    """Property-based tests for cross-enum invariants."""

    @given(
        st.sampled_from(list(EnumMessageCategory)),
        st.sampled_from(list(EnumExecutionShape)),
    )
    @settings(max_examples=100)
    def test_shape_category_bidirectional_consistency(
        self, category: EnumMessageCategory, shape: EnumExecutionShape
    ) -> None:
        """Property: Shape's source category lookup is consistent with get_shapes_for_category."""
        source_category = EnumExecutionShape.get_source_category(shape)
        shapes_for_source = EnumExecutionShape.get_shapes_for_category(source_category)

        # The shape must be in the list of shapes for its source category
        assert shape in shapes_for_source

        # If shape is in category's shapes, source must be that category
        if shape in EnumExecutionShape.get_shapes_for_category(category):
            assert source_category == category

    @given(st.sampled_from(["orchestrator", "effect", "reducer"]))
    @settings(max_examples=50)
    def test_valid_targets_have_shapes(self, target: str) -> None:
        """Property: Each valid target must have at least one shape."""
        shapes = EnumExecutionShape.get_shapes_for_target(target)
        assert len(shapes) >= 1, f"Target {target} has no execution shapes"

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_invalid_topics_return_none(self, random_text: str) -> None:
        """Property: Random strings without category markers return None."""
        # Only test strings that don't accidentally contain valid markers
        if not any(
            marker in random_text.lower()
            for marker in [".events", ".commands", ".intents"]
        ):
            result = EnumMessageCategory.from_topic(random_text)
            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
