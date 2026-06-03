# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for topic-migration contract + topic↔schema linkage (OMN-12621)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_cutover_criterion import EnumCutoverCriterion
from omnibase_core.enums.enum_migration_phase import EnumMigrationPhase
from omnibase_core.enums.enum_topic_schema_delta import EnumTopicSchemaDelta
from omnibase_core.models.contracts.model_topic_migration_contract import (
    ModelTopicMigrationContract,
)
from omnibase_core.models.contracts.model_topic_schema_binding import (
    ModelTopicSchemaBinding,
    build_versioned_topic,
    detect_breaking_delta,
    parse_canonical_topic,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


def _sv(major: int, minor: int = 0, patch: int = 0) -> ModelSemVer:
    return ModelSemVer(major=major, minor=minor, patch=patch)


def _binding(topic: str, event: str, sv: ModelSemVer) -> ModelTopicSchemaBinding:
    return ModelTopicSchemaBinding(topic=topic, event_name=event, schema_version=sv)


# ---------------------------------------------------------------------------
# Topic parsing + general builder
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTopicParsingAndBuilder:
    def test_parse_canonical_topic(self) -> None:
        parsed = parse_canonical_topic("onex.evt.payments.payment-captured.v2")
        assert parsed.namespace == "onex"
        assert parsed.kind == "evt"
        assert parsed.service == "payments"
        assert parsed.event == "payment-captured"
        assert parsed.topic_major == 2

    def test_parse_rejects_non_canonical(self) -> None:
        with pytest.raises(ValueError):
            parse_canonical_topic("not-a-topic")

    def test_build_versioned_topic(self) -> None:
        assert (
            build_versioned_topic("payments", "payment-captured", 2)
            == "onex.evt.payments.payment-captured.v2"
        )

    def test_build_versioned_topic_rejects_bad_version(self) -> None:
        with pytest.raises(ValueError):
            build_versioned_topic("payments", "payment-captured", 0)


# ---------------------------------------------------------------------------
# Topic ↔ schema_version linkage
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTopicSchemaBinding:
    def test_binding_major_matches_topic_version(self) -> None:
        b = _binding(
            "onex.evt.payments.payment-captured.v2", "PAYMENT_CAPTURED", _sv(2)
        )
        assert b.parsed.topic_major == b.schema_version.major == 2

    def test_binding_major_mismatch_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _binding(
                "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(2)
            )


# ---------------------------------------------------------------------------
# Breaking-delta detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBreakingDeltaDetection:
    def test_no_change(self) -> None:
        old = _binding(
            "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
        )
        new = _binding(
            "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
        )
        delta = detect_breaking_delta(old, new)
        assert delta is EnumTopicSchemaDelta.NONE
        assert not delta.is_breaking

    def test_minor_bump_is_compatible(self) -> None:
        old = _binding(
            "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1, 0)
        )
        new = _binding(
            "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1, 1)
        )
        delta = detect_breaking_delta(old, new)
        assert delta is EnumTopicSchemaDelta.COMPATIBLE
        assert not delta.is_breaking

    def test_major_bump_is_breaking(self) -> None:
        old = _binding(
            "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
        )
        new = _binding(
            "onex.evt.payments.payment-captured.v2", "PAYMENT_CAPTURED", _sv(2)
        )
        delta = detect_breaking_delta(old, new)
        assert delta is EnumTopicSchemaDelta.MAJOR_BUMP
        assert delta.is_breaking

    def test_namespace_rename_is_breaking(self) -> None:
        old = _binding("onex.evt.oldns.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1))
        new = _binding("onex.evt.newns.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1))
        delta = detect_breaking_delta(old, new)
        assert delta is EnumTopicSchemaDelta.NAMESPACE_RENAME
        assert delta.is_breaking


# ---------------------------------------------------------------------------
# ModelTopicMigrationContract
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTopicMigrationContract:
    def _vbump_contract(self) -> ModelTopicMigrationContract:
        return ModelTopicMigrationContract(
            contract_version=_sv(1),
            ticket="OMN-12621",
            old_binding=_binding(
                "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
            ),
            new_binding=_binding(
                "onex.evt.payments.payment-captured.v2", "PAYMENT_CAPTURED", _sv(2)
            ),
            old_consumer_group="payments-ledger-v1",
            new_consumer_group="payments-ledger-v2",
            compatibility_window_hours=72,
            cutover_criteria=(
                EnumCutoverCriterion.OLD_TOPIC_DRAINED,
                EnumCutoverCriterion.NEW_TOPIC_CONSUMER_HEALTHY,
            ),
        )

    def test_valid_version_bump_migration(self) -> None:
        c = self._vbump_contract()
        assert c.phase is EnumMigrationPhase.PLANNED
        assert c.delta is EnumTopicSchemaDelta.MAJOR_BUMP
        assert not c.is_namespace_rename
        assert c.drain_proof_required is True

    def test_namespace_rename_migration(self) -> None:
        c = ModelTopicMigrationContract(
            contract_version=_sv(1),
            ticket="OMN-12407",
            old_binding=_binding(
                "onex.evt.oldns.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
            ),
            new_binding=_binding(
                "onex.evt.newns.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
            ),
            old_consumer_group="oldns-ledger",
            new_consumer_group="newns-ledger",
            compatibility_window_hours=48,
            cutover_criteria=(EnumCutoverCriterion.OLD_TOPIC_DRAINED,),
        )
        assert c.is_namespace_rename
        assert c.delta is EnumTopicSchemaDelta.NAMESPACE_RENAME

    def test_frozen(self) -> None:
        c = self._vbump_contract()
        with pytest.raises(Exception):
            c.compatibility_window_hours = 1  # type: ignore[misc]

    def test_non_breaking_delta_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModelTopicMigrationContract(
                contract_version=_sv(1),
                ticket="OMN-12621",
                old_binding=_binding(
                    "onex.evt.payments.payment-captured.v1",
                    "PAYMENT_CAPTURED",
                    _sv(1, 0),
                ),
                new_binding=_binding(
                    "onex.evt.payments.payment-captured.v1",
                    "PAYMENT_CAPTURED",
                    _sv(1, 1),
                ),
                old_consumer_group="a",
                new_consumer_group="b",
                compatibility_window_hours=1,
                cutover_criteria=(EnumCutoverCriterion.OLD_TOPIC_DRAINED,),
            )

    def test_drain_proof_gate_requires_drained_criterion(self) -> None:
        with pytest.raises(ValidationError):
            ModelTopicMigrationContract(
                contract_version=_sv(1),
                ticket="OMN-12621",
                old_binding=_binding(
                    "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
                ),
                new_binding=_binding(
                    "onex.evt.payments.payment-captured.v2", "PAYMENT_CAPTURED", _sv(2)
                ),
                old_consumer_group="a",
                new_consumer_group="b",
                compatibility_window_hours=1,
                drain_proof_required=True,
                cutover_criteria=(EnumCutoverCriterion.NEW_TOPIC_CONSUMER_HEALTHY,),
            )

    def test_open_ended_window_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelTopicMigrationContract(
                contract_version=_sv(1),
                ticket="OMN-12621",
                old_binding=_binding(
                    "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
                ),
                new_binding=_binding(
                    "onex.evt.payments.payment-captured.v2", "PAYMENT_CAPTURED", _sv(2)
                ),
                old_consumer_group="a",
                new_consumer_group="b",
                compatibility_window_hours=0,
                cutover_criteria=(EnumCutoverCriterion.OLD_TOPIC_DRAINED,),
            )

    def test_bad_ticket_rejected(self) -> None:
        with pytest.raises(Exception):
            ModelTopicMigrationContract(
                contract_version=_sv(1),
                ticket="not-a-ticket",
                old_binding=_binding(
                    "onex.evt.payments.payment-captured.v1", "PAYMENT_CAPTURED", _sv(1)
                ),
                new_binding=_binding(
                    "onex.evt.payments.payment-captured.v2", "PAYMENT_CAPTURED", _sv(2)
                ),
                old_consumer_group="a",
                new_consumer_group="b",
                compatibility_window_hours=1,
                cutover_criteria=(EnumCutoverCriterion.OLD_TOPIC_DRAINED,),
            )
