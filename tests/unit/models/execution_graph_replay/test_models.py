# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphAnchorKind,
    EnumExecutionGraphAnchorState,
    EnumExecutionGraphCursorMode,
    EnumExecutionGraphEdgeKind,
    EnumExecutionGraphEndpointKind,
    EnumExecutionGraphNodeKind,
    EnumExecutionGraphRefusalReason,
    EnumExecutionGraphUnresolvedReason,
    EnumExecutionGraphVerdictOutcome,
    EnumExecutionGraphVerdictStatus,
)
from omnibase_core.models.execution_graph_replay import (
    ModelExecutionGraph,
    ModelExecutionGraphAnchor,
    ModelExecutionGraphAnnotations,
    ModelExecutionGraphEdge,
    ModelExecutionGraphEndpoint,
    ModelExecutionGraphLabel,
    ModelExecutionGraphNode,
    ModelExecutionGraphReplay,
    ModelExecutionGraphReplayPolicy,
    ModelExecutionGraphRequest,
    ModelExecutionGraphSourceCursor,
    ModelExecutionGraphSourceRef,
    ModelExecutionGraphTopologyVersion,
    ModelExecutionGraphUnresolved,
    ModelExecutionGraphVerdict,
)

CORRELATION_ID = UUID("057d45de-f73c-4005-9127-c7e786f7efa4")
ENVELOPE_ID = UUID("3ac96e39-3d53-4995-88f8-c32bb34e8e0f")
PARENT_ID = UUID("b21363a7-0dc4-4ed2-ae9a-5fefb03d8d6e")


def source_ref(offset: int = 20) -> ModelExecutionGraphSourceRef:
    return ModelExecutionGraphSourceRef(
        topic="onex.evt.omnimarket.delegation-request.v1",
        partition=0,
        kafka_offset=offset,
    )


def node(
    *,
    node_id: UUID = ENVELOPE_ID,
    parent_id: UUID | None = None,
    offset: int = 20,
) -> ModelExecutionGraphNode:
    return ModelExecutionGraphNode(
        id=node_id,
        kind=EnumExecutionGraphNodeKind.HOP,
        topic=source_ref(offset).topic,
        partition=0,
        kafka_offset=offset,
        parent_envelope_id=parent_id,
        replay_green=True,
        verifier_verdict="pass",
        source_ref=source_ref(offset),
    )


def test_source_cursor_is_partition_scoped_ingest_bound_and_rejects_nonpositive_positions() -> (
    None
):
    cursor = ModelExecutionGraphSourceCursor(
        topic="onex.evt.omnimarket.delegation-request.v1",
        partition=1,
        max_ingest_watermark=42,
    )
    assert (
        cursor.topic,
        cursor.partition,
        cursor.max_ingest_watermark,
    ) == (
        "onex.evt.omnimarket.delegation-request.v1",
        1,
        42,
    )
    with pytest.raises(ValidationError):
        ModelExecutionGraphSourceCursor(
            topic=cursor.topic, partition=-1, max_ingest_watermark=1
        )
    with pytest.raises(ValidationError):
        ModelExecutionGraphSourceCursor(
            topic=cursor.topic, partition=0, max_ingest_watermark=0
        )


def test_source_ref_is_the_recorded_kafka_position_without_a_watermark_claim() -> None:
    source = ModelExecutionGraphSourceRef(
        topic="onex.evt.omnimarket.delegation-request.v1",
        partition=0,
        kafka_offset=8,
    )
    assert source.kafka_offset == 8
    with pytest.raises(ValidationError):
        ModelExecutionGraphSourceRef(
            topic=source.topic,
            partition=source.partition,
            kafka_offset=-1,
        )


def test_request_has_no_tenant_override_and_rejects_duplicate_cursor_keys() -> None:
    request = ModelExecutionGraphRequest(
        correlation_id=CORRELATION_ID,
        cursor_mode=EnumExecutionGraphCursorMode.BOUNDED,
        source_cursors=[
            ModelExecutionGraphSourceCursor(
                topic=source_ref().topic,
                partition=0,
                max_ingest_watermark=30,
            )
        ],
    )
    assert request.correlation_id == CORRELATION_ID
    with pytest.raises(ValidationError):
        ModelExecutionGraphRequest.model_validate(
            {
                "correlation_id": str(CORRELATION_ID),
                "cursor_mode": "latest",
                "tenant_id": "tenant-a",
                "source_cursors": None,
            }
        )

    cursor = request.source_cursors[0]
    with pytest.raises(ValidationError, match="duplicate"):
        ModelExecutionGraphRequest(
            correlation_id=CORRELATION_ID,
            cursor_mode=EnumExecutionGraphCursorMode.BOUNDED,
            source_cursors=[cursor, cursor],
        )

    assert (
        ModelExecutionGraphRequest(
            correlation_id=CORRELATION_ID,
            cursor_mode=EnumExecutionGraphCursorMode.LATEST,
        ).source_cursors
        is None
    )
    with pytest.raises(ValidationError, match="non-empty"):
        ModelExecutionGraphRequest(
            correlation_id=CORRELATION_ID,
            cursor_mode=EnumExecutionGraphCursorMode.BOUNDED,
            source_cursors=[],
        )


def test_read_model_splits_deterministic_replay_from_labels_and_current_annotations() -> (
    None
):
    ref = source_ref()
    anchor = ModelExecutionGraphAnchor(
        kind=EnumExecutionGraphAnchorKind.SESSION,
        session_id="session-1",
        evidence_ref=ref,
        state=EnumExecutionGraphAnchorState.RESOLVED,
    )
    graph = ModelExecutionGraph(
        schema_version=1,
        replay=ModelExecutionGraphReplay(
            fold_version={"major": 1, "minor": 0, "patch": 0},
            topology_version=ModelExecutionGraphTopologyVersion(
                contract_version={"major": 1, "minor": 0, "patch": 0},
                topology_sha256="a" * 64,
            ),
            grader_version={"major": 1, "minor": 0, "patch": 0},
            verdict_reducer_version={"major": 1, "minor": 0, "patch": 0},
            policy=ModelExecutionGraphReplayPolicy(
                traversal="parent_topological",
                node_identity="envelope_id",
                redelivery="same_id_exact_redelivery_lowest_source_position",
                conflicting_identity="same_id_conflicting_parent_or_semantic_body_refuse",
                cross_topic_duplicate="same_id_across_topics_refuse",
            ),
            source_cursors=[
                ModelExecutionGraphSourceCursor(
                    topic=ref.topic,
                    partition=ref.partition,
                    max_ingest_watermark=100,
                )
            ],
            correlation_id=CORRELATION_ID,
            anchor=anchor,
            nodes=[node(node_id=PARENT_ID, offset=19), node()],
            edges=[
                ModelExecutionGraphEdge(
                    id="caused:parent:child",
                    from_id=ModelExecutionGraphEndpoint(
                        kind=EnumExecutionGraphEndpointKind.NODE, node_id=PARENT_ID
                    ),
                    to_id=ModelExecutionGraphEndpoint(
                        kind=EnumExecutionGraphEndpointKind.NODE, node_id=ENVELOPE_ID
                    ),
                    kind=EnumExecutionGraphEdgeKind.CAUSED,
                    evidence_ref=ref,
                ),
                ModelExecutionGraphEdge(
                    id="anchored:session:parent",
                    from_id=ModelExecutionGraphEndpoint(
                        kind=EnumExecutionGraphEndpointKind.SESSION_ANCHOR,
                        session_id="session-1",
                    ),
                    to_id=ModelExecutionGraphEndpoint(
                        kind=EnumExecutionGraphEndpointKind.NODE, node_id=PARENT_ID
                    ),
                    kind=EnumExecutionGraphEdgeKind.ANCHORED,
                    evidence_ref=ref,
                ),
                ModelExecutionGraphEdge(
                    id="verified:child:verdict",
                    from_id=ModelExecutionGraphEndpoint(
                        kind=EnumExecutionGraphEndpointKind.NODE, node_id=ENVELOPE_ID
                    ),
                    to_id=ModelExecutionGraphEndpoint(
                        kind=EnumExecutionGraphEndpointKind.VERDICT,
                        verdict_id=UUID("7fce85b8-90e9-4da2-94fa-c8f36e70a60c"),
                    ),
                    kind=EnumExecutionGraphEdgeKind.VERIFIED,
                    evidence_ref=ref,
                ),
            ],
            order=[PARENT_ID, ENVELOPE_ID],
            verdicts=[
                ModelExecutionGraphVerdict(
                    id=UUID("7fce85b8-90e9-4da2-94fa-c8f36e70a60c"),
                    delegation_correlation_id=CORRELATION_ID,
                    status=EnumExecutionGraphVerdictStatus.VERIFIED,
                    outcome=EnumExecutionGraphVerdictOutcome.DONE,
                    outcome_refusal=None,
                    source_ref=ref,
                )
            ],
            unresolved=[
                ModelExecutionGraphUnresolved(
                    subject_id=ENVELOPE_ID,
                    reason=EnumExecutionGraphUnresolvedReason.MISSING_PARENT,
                    source_ref=ref,
                )
            ],
            withheld_count=0,
            refusal=None,
        ),
        labels=[
            ModelExecutionGraphLabel(
                node_id=ENVELOPE_ID,
                event_timestamp=datetime(2026, 9, 26, tzinfo=UTC),
                ledger_written_at=datetime(2026, 9, 26, tzinfo=UTC),
            )
        ],
        annotations=ModelExecutionGraphAnnotations(
            read_at=datetime(2026, 9, 26, tzinfo=UTC),
            authorization_tenant_id=UUID("55945d66-bec5-4c2a-b827-5cf27b704534"),
            authorization_ownership_source="delegation_events",
            authorization_checked_over="full_correlation",
            stored_chain=[],
            stored_verdicts=[],
        ),
    )
    assert graph.replay.topology_version.contract_version.major == 1
    assert graph.replay.order == (PARENT_ID, ENVELOPE_ID)
    assert isinstance(graph.replay.nodes, tuple)
    assert isinstance(graph.annotations.stored_chain, tuple)
    assert isinstance(graph.model_dump(mode="json")["replay"]["nodes"], list)
    with pytest.raises(TypeError):
        graph.replay.nodes[0] = node()  # type: ignore[index]
    assert graph.labels[0].node_id == ENVELOPE_ID
    assert graph.annotations.authorization_tenant_id == UUID(
        "55945d66-bec5-4c2a-b827-5cf27b704534"
    )
    assert graph.replay.refusal is None


def test_repeated_envelope_id_with_conflicting_parent_or_semantic_body_is_invalid() -> (
    None
):
    def replay_with(nodes: list[ModelExecutionGraphNode]) -> ModelExecutionGraphReplay:
        return ModelExecutionGraphReplay(
            fold_version={"major": 1, "minor": 0, "patch": 0},
            topology_version={
                "contract_version": {"major": 1, "minor": 0, "patch": 0},
                "topology_sha256": "b" * 64,
            },
            grader_version={"major": 1, "minor": 0, "patch": 0},
            verdict_reducer_version={"major": 1, "minor": 0, "patch": 0},
            policy={
                "traversal": "parent_topological",
                "node_identity": "envelope_id",
                "redelivery": "same_id_exact_redelivery_lowest_source_position",
                "conflicting_identity": "same_id_conflicting_parent_or_semantic_body_refuse",
                "cross_topic_duplicate": "same_id_across_topics_refuse",
            },
            source_cursors=[],
            correlation_id=CORRELATION_ID,
            anchor=ModelExecutionGraphAnchor(
                kind=EnumExecutionGraphAnchorKind.NONE,
                state=EnumExecutionGraphAnchorState.UNRESOLVED,
            ),
            nodes=nodes,
            edges=[],
            order=[ENVELOPE_ID],
            verdicts=[],
            unresolved=[],
            withheld_count=0,
        )

    with pytest.raises(ValidationError, match=r"duplicate|envelope"):
        replay_with([node(), node(parent_id=PARENT_ID)])

    semantic_conflict = node().model_dump()
    semantic_conflict["replay_green"] = False
    with pytest.raises(ValidationError, match=r"duplicate|envelope"):
        replay_with([node(), ModelExecutionGraphNode.model_validate(semantic_conflict)])


def test_graph_models_are_frozen_extra_forbid_and_refusal_is_typed() -> None:
    ref = source_ref()
    with pytest.raises(ValidationError):
        ModelExecutionGraphSourceRef(topic=ref.topic, partition=0, kafka_offset=1, x=1)
    with pytest.raises(ValidationError):
        ref.topic = "changed"  # type: ignore[misc]
    assert (
        EnumExecutionGraphRefusalReason.CORRELATION_NOT_FOUND.value
        == "correlation_not_found"
    )
