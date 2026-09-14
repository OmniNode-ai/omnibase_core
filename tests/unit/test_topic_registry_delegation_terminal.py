# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Registry + TopicBase coverage for the five delegation terminal topics (OMN-15622).

Scoped slice of OMN-15622: the delegation terminal family only. This takes the
BACKFILL disposition for that family — the two v1 terminal topics and the three
v2 terminal topics become rows in ``contracts/topic_registry.yaml`` with a
durability tier and a schema ref. The parent ticket's two-direction set-drift
checker (``TopicBase - registry`` and ``registry - TopicBase`` over the whole
145-member enum) is NOT delivered here and is NOT answered by these tests.

The three v2 names come from the operator-approved delegation v2 plan and from
the terminal classes that landed in omnibase_core#1653 (squash ``469cccb4``,
OMN-17841). The v2 shape is THREE classes, one topic each:

* ``ModelDelegationTerminalCompletedV2``      -> ``...delegation-completed.v2``
* ``ModelDelegationTerminalFailedRoutedV2``   -> ``...delegation-failed-routed.v2``
* ``ModelDelegationTerminalFailedUnroutedV2`` -> ``...delegation-failed-unrouted.v2``

A two-topic shape that put both failed classes on one ``delegation-failed.v2``
topic is refused by ``assert_published_events_injective``; the negative test
below is the mechanical proof of that, so the wrong shape cannot come back
silently.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml

from omnibase_core.models.delegation.wire import (
    ModelDelegationTerminalCompletedV2,
    ModelDelegationTerminalFailedRoutedV2,
    ModelDelegationTerminalFailedUnroutedV2,
)
from omnibase_core.runtime.runtime_fanout_resolver import (
    assert_published_events_injective,
    derive_event_type_from_topic,
)
from omnibase_core.topics import _CANONICAL_TOPIC_PATTERN, TopicBase

pytestmark = pytest.mark.unit

_TOPICS_SOURCE = Path(__file__).resolve().parents[2] / "src/omnibase_core/topics.py"
_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/omnibase_core/contracts/topic_registry.yaml"
)

DELEGATION_TERMINAL_CONSTANTS: tuple[str, ...] = (
    "DELEGATION_COMPLETED_INFRA",
    "DELEGATION_FAILED_INFRA",
    "DELEGATION_COMPLETED_INFRA_V2",
    "DELEGATION_FAILED_ROUTED_INFRA_V2",
    "DELEGATION_FAILED_UNROUTED_INFRA_V2",
)

DELEGATION_TERMINAL_TOPICS: tuple[str, ...] = (
    "onex.evt.omnibase-infra.delegation-completed.v1",
    "onex.evt.omnibase-infra.delegation-failed.v1",
    "onex.evt.omnibase-infra.delegation-completed.v2",
    "onex.evt.omnibase-infra.delegation-failed-routed.v2",
    "onex.evt.omnibase-infra.delegation-failed-unrouted.v2",
)


def _declaration_source(constant: str) -> str | None:
    """Return the full source text of ``TopicBase.<constant>``'s assignment statement.

    Spans the whole statement, not just its first line, so a value wrapped in
    parentheses to stay inside the 88-column limit still shows its trailing
    ``# onex-topic-sot`` marker.
    """
    source = _TOPICS_SOURCE.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "TopicBase":
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id == constant:
                    end = statement.end_lineno or statement.lineno
                    return "\n".join(lines[statement.lineno - 1 : end])
    return None


def _registry_rows() -> list[dict[str, Any]]:
    loaded = yaml.safe_load(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return list(loaded["topics"])


def _registry_row(topic: str) -> dict[str, Any]:
    for row in _registry_rows():
        if row["topic"] == topic:
            return row
    raise AssertionError(
        f"topic_registry.yaml has no row for {topic!r}; "
        f"present rows: {sorted(r['topic'] for r in _registry_rows())}"
    )


# ---------------------------------------------------------------------------
# TopicBase constants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("constant", "topic"),
    list(zip(DELEGATION_TERMINAL_CONSTANTS, DELEGATION_TERMINAL_TOPICS, strict=True)),
)
def test_delegation_terminal_constant_wire_value(constant: str, topic: str) -> None:
    """Each terminal constant carries exactly the canonical wire name."""
    assert getattr(TopicBase, constant) == topic


@pytest.mark.parametrize("topic", DELEGATION_TERMINAL_TOPICS)
def test_delegation_terminal_topic_matches_canonical_pattern(topic: str) -> None:
    """Every one of the five matches the canonical ONEX topic pattern."""
    assert _CANONICAL_TOPIC_PATTERN.match(topic) is not None, (
        f"{topic!r} does not match the canonical "
        "onex.{kind}.{producer}.{event-name}.v{n} pattern"
    )


@pytest.mark.parametrize("topic", DELEGATION_TERMINAL_TOPICS)
def test_delegation_terminal_topic_derives_event_type(topic: str) -> None:
    """A null event_type at the emit boundary is a silent type-scoped drop (OMN-14743)."""
    assert derive_event_type_from_topic(topic) is not None


def test_v2_terminal_topics_derive_distinct_event_types() -> None:
    """The three v2 topics must not collapse onto one routing key."""
    derived = {derive_event_type_from_topic(t) for t in DELEGATION_TERMINAL_TOPICS[2:]}
    assert len(derived) == 3, f"v2 event_type derivation is not injective: {derived}"


@pytest.mark.parametrize("constant", DELEGATION_TERMINAL_CONSTANTS)
def test_delegation_terminal_constant_carries_sot_marker(constant: str) -> None:
    """The registry mandates the ``# onex-topic-sot`` marker on the enum member.

    ``topic_registry.yaml:22-27`` requires it for every registered topic. The two
    v1 constants lacked it; this asserts the backfill as well as the new v2 ones.
    """
    declaration = _declaration_source(constant)
    assert declaration is not None, f"{constant} is not declared in topics.py"
    assert "# onex-topic-sot" in declaration, (
        f"{constant} is registered in topic_registry.yaml but its declaration "
        "carries no '# onex-topic-sot' marker"
    )


# ---------------------------------------------------------------------------
# topic_registry.yaml rows
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("topic", DELEGATION_TERMINAL_TOPICS)
def test_registry_row_exists(topic: str) -> None:
    assert _registry_row(topic)["topic"] == topic


@pytest.mark.parametrize("topic", DELEGATION_TERMINAL_TOPICS)
def test_registry_row_declares_durability_tier(topic: str) -> None:
    """Terminal delegation events are audit/projection inputs, so they are durable."""
    assert _registry_row(topic)["durability_tier"] == "durable"


@pytest.mark.parametrize("topic", DELEGATION_TERMINAL_TOPICS)
def test_registry_row_declares_owner(topic: str) -> None:
    assert _registry_row(topic)["owner"]


@pytest.mark.parametrize(
    ("topic", "schema_ref"),
    [
        (
            "onex.evt.omnibase-infra.delegation-completed.v2",
            "omnibase_core.models.delegation.wire.model_delegation_terminal_v2."
            "ModelDelegationTerminalCompletedV2",
        ),
        (
            "onex.evt.omnibase-infra.delegation-failed-routed.v2",
            "omnibase_core.models.delegation.wire.model_delegation_terminal_v2."
            "ModelDelegationTerminalFailedRoutedV2",
        ),
        (
            "onex.evt.omnibase-infra.delegation-failed-unrouted.v2",
            "omnibase_core.models.delegation.wire.model_delegation_terminal_v2."
            "ModelDelegationTerminalFailedUnroutedV2",
        ),
    ],
)
def test_v2_registry_row_schema_ref_points_at_the_landed_class(
    topic: str, schema_ref: str
) -> None:
    """Each v2 row's schema_ref names the class omnibase_core#1653 landed."""
    assert _registry_row(topic)["schema_ref"] == schema_ref


def test_registry_topic_names_are_topicbase_values() -> None:
    """The registry's resolution contract: every row's name is a TopicBase value."""
    values = set(TopicBase._value2member_map_)
    for topic in DELEGATION_TERMINAL_TOPICS:
        assert _registry_row(topic)["topic"] in values


def test_registry_delegation_row_count_is_five() -> None:
    """The ticket's PROBED criterion, asserted in-tree (baseline was 0)."""
    delegation_rows = [
        row
        for row in _registry_rows()
        if str(row["topic"]).startswith("onex.evt.omnibase-infra.delegation-")
    ]
    assert len(delegation_rows) == 5, sorted(r["topic"] for r in delegation_rows)


# ---------------------------------------------------------------------------
# Negative: the rejected two-topic shape cannot come back
# ---------------------------------------------------------------------------


def test_collapsing_the_three_v2_classes_onto_one_topic_is_refused() -> None:
    """Three distinct wire classes on one topic is a non-injective map and RAISES.

    This is why the v2 family is three topics and not two: a single
    ``delegation-failed.v2`` topic carrying both failed classes is refused here.
    """
    collapsed = {
        ModelDelegationTerminalCompletedV2.__name__: (
            "onex.evt.omnibase-infra.delegation-completed.v2"
        ),
        ModelDelegationTerminalFailedRoutedV2.__name__: (
            "onex.evt.omnibase-infra.delegation-completed.v2"
        ),
        ModelDelegationTerminalFailedUnroutedV2.__name__: (
            "onex.evt.omnibase-infra.delegation-completed.v2"
        ),
    }
    with pytest.raises(Exception, match="injective"):
        assert_published_events_injective(
            collapsed, context="OMN-15622 collapsed v2 terminal family"
        )


def test_the_two_failed_classes_on_one_failed_topic_is_refused() -> None:
    """The exact rejected two-name shape: both failed classes on delegation-failed.v2."""
    two_name_shape = {
        ModelDelegationTerminalCompletedV2.__name__: (
            "onex.evt.omnibase-infra.delegation-completed.v2"
        ),
        ModelDelegationTerminalFailedRoutedV2.__name__: (
            "onex.evt.omnibase-infra.delegation-failed.v2"
        ),
        ModelDelegationTerminalFailedUnroutedV2.__name__: (
            "onex.evt.omnibase-infra.delegation-failed.v2"
        ),
    }
    with pytest.raises(Exception, match="injective"):
        assert_published_events_injective(
            two_name_shape, context="OMN-15622 rejected two-name v2 shape"
        )


def test_the_canonical_three_topic_map_is_accepted() -> None:
    """Positive control: the shape this task lands passes the same assertion."""
    assert_published_events_injective(
        {
            ModelDelegationTerminalCompletedV2.__name__: (
                "onex.evt.omnibase-infra.delegation-completed.v2"
            ),
            ModelDelegationTerminalFailedRoutedV2.__name__: (
                "onex.evt.omnibase-infra.delegation-failed-routed.v2"
            ),
            ModelDelegationTerminalFailedUnroutedV2.__name__: (
                "onex.evt.omnibase-infra.delegation-failed-unrouted.v2"
            ),
        },
        context="OMN-15622 canonical v2 terminal family",
    )
