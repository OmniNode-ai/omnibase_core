# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ModelKnowledgeContextBundle and sub-models (OMN-11928)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnibase_core.enums.enum_knowledge_provider_kind import EnumKnowledgeProviderKind


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 5, 24, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def provenance(now: datetime):
    from omnibase_core.models.context.model_context_provenance import (
        ModelContextProvenance,
    )

    return ModelContextProvenance(
        provider_kind=EnumKnowledgeProviderKind.DOCUMENT_STORE,
        provider_name="omnimemory",
        source_id="doc-abc123",
        source_hash="sha256:abc",
        retrieved_at=now,
        confidence=0.9,
    )


@pytest.fixture
def adr_summary(provenance):
    from omnibase_core.models.context.model_adr_summary import ModelADRSummary

    return ModelADRSummary(
        adr_id="ADR-001",
        title="Use Pydantic for all models",
        decision="All data models use Pydantic BaseModel",
        status="accepted",
        provenance=provenance,
    )


@pytest.fixture
def antipattern_summary(provenance):
    from omnibase_core.models.context.model_antipattern_summary import (
        ModelAntipatternSummary,
    )

    return ModelAntipatternSummary(
        name="no-optional-type",
        severity="ERROR",
        category="code_quality",
        description="Use X | None not Optional[X]",
        provenance=provenance,
    )


@pytest.fixture
def learning_match(provenance):
    from omnibase_core.models.context.model_learning_match import ModelLearningMatch

    return ModelLearningMatch(
        learning_id="learn-001",
        summary="Always use uv run for Python commands",
        relevance_score=0.85,
        provenance=provenance,
    )


@pytest.fixture
def graph_snapshot(provenance):
    from omnibase_core.models.context.model_graph_snapshot import ModelGraphSnapshot

    return ModelGraphSnapshot(
        node_count=42,
        edge_count=88,
        summary="omnibase_core depends on omnibase_compat",
        provenance=provenance,
    )


class TestModelContextProvenance:
    def test_frozen(self, provenance) -> None:
        with pytest.raises(Exception):
            provenance.provider_name = "changed"  # type: ignore[misc]

    def test_extra_forbid(self, now: datetime) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.context.model_context_provenance import (
            ModelContextProvenance,
        )

        with pytest.raises(ValidationError):
            ModelContextProvenance(
                provider_kind=EnumKnowledgeProviderKind.CODE_INDEX,
                provider_name="x",
                source_id="y",
                source_hash="z",
                retrieved_at=now,
                confidence=0.5,
                extra_field="boom",  # type: ignore[call-arg]
            )

    def test_confidence_bounds(self, now: datetime) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.context.model_context_provenance import (
            ModelContextProvenance,
        )

        with pytest.raises(ValidationError):
            ModelContextProvenance(
                provider_kind=EnumKnowledgeProviderKind.CODE_INDEX,
                provider_name="x",
                source_id="y",
                source_hash="z",
                retrieved_at=now,
                confidence=1.5,
            )

    def test_provider_kind_rejects_free_text(self, now: datetime) -> None:
        """The provider CLASS is a closed set; a vendor string is not a kind."""
        from pydantic import ValidationError

        from omnibase_core.models.context.model_context_provenance import (
            ModelContextProvenance,
        )

        with pytest.raises(ValidationError):
            ModelContextProvenance(
                provider_kind="some_vendor_product",  # type: ignore[arg-type]
                provider_name="some_vendor_product",
                source_id="y",
                source_hash="z",
                retrieved_at=now,
                confidence=0.5,
            )

    @pytest.mark.parametrize("kind", list(EnumKnowledgeProviderKind))
    def test_round_trips_for_every_provider_kind(
        self, kind: EnumKnowledgeProviderKind, now: datetime
    ) -> None:
        """OMN-18372 AC2 — every kind is generic and survives a dump/validate.

        The vendor identity rides in provider_name as data, so a provenance
        record naming a backend this repo has never heard of is still valid.
        """
        from omnibase_core.models.context.model_context_provenance import (
            ModelContextProvenance,
        )

        original = ModelContextProvenance(
            provider_kind=kind,
            provider_name="an-unaffiliated-backend",
            source_id="doc-1",
            source_hash="sha256:abc",
            retrieved_at=now,
            confidence=0.75,
        )
        restored = ModelContextProvenance.model_validate(original.model_dump())
        assert restored == original
        assert restored.provider_kind is kind
        assert restored.provider_name == "an-unaffiliated-backend"


class TestModelADRSummary:
    def test_fields(self, adr_summary) -> None:
        assert adr_summary.adr_id == "ADR-001"
        assert adr_summary.status == "accepted"

    def test_frozen(self, adr_summary) -> None:
        with pytest.raises(Exception):
            adr_summary.title = "changed"  # type: ignore[misc]


class TestModelAntipatternSummary:
    def test_fields(self, antipattern_summary) -> None:
        assert antipattern_summary.severity == "ERROR"
        assert antipattern_summary.category == "code_quality"

    def test_frozen(self, antipattern_summary) -> None:
        with pytest.raises(Exception):
            antipattern_summary.name = "changed"  # type: ignore[misc]


class TestModelLearningMatch:
    def test_fields(self, learning_match) -> None:
        assert learning_match.relevance_score == 0.85

    def test_frozen(self, learning_match) -> None:
        with pytest.raises(Exception):
            learning_match.summary = "changed"  # type: ignore[misc]


class TestModelGraphSnapshot:
    def test_fields(self, graph_snapshot) -> None:
        assert graph_snapshot.node_count == 42
        assert graph_snapshot.edge_count == 88

    def test_frozen(self, graph_snapshot) -> None:
        with pytest.raises(Exception):
            graph_snapshot.node_count = 0  # type: ignore[misc]


class TestModelKnowledgeContextBundle:
    def _make_l0(self, antipattern_summary, now: datetime):
        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        return ModelKnowledgeContextBundle(
            repo="omnibase_core",
            ticket_id=None,
            architecture_context="",
            relevant_adrs=(),
            applicable_antipatterns=(antipattern_summary,),
            prior_learnings=(),
            dependency_graph=None,
            bundle_level="L0",
            degraded=False,
            degraded_providers=(),
            missing_sections=(),
            bundle_hash="abc123",
            generated_at=now,
        )

    def _make_l1(self, antipattern_summary, adr_summary, now: datetime):
        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        return ModelKnowledgeContextBundle(
            repo="omnibase_core",
            ticket_id="OMN-11928",
            architecture_context="",
            relevant_adrs=(adr_summary,),
            applicable_antipatterns=(antipattern_summary,),
            prior_learnings=(),
            dependency_graph=None,
            bundle_level="L1",
            degraded=False,
            degraded_providers=(),
            missing_sections=(),
            bundle_hash="def456",
            generated_at=now,
        )

    def _make_l2(self, antipattern_summary, adr_summary, now: datetime):
        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        return ModelKnowledgeContextBundle(
            repo="omnibase_core",
            ticket_id="OMN-11928",
            architecture_context="Architecture: layered, contract-first.",
            relevant_adrs=(adr_summary,),
            applicable_antipatterns=(antipattern_summary,),
            prior_learnings=(),
            dependency_graph=None,
            bundle_level="L2",
            degraded=False,
            degraded_providers=(),
            missing_sections=(),
            bundle_hash="ghi789",
            generated_at=now,
        )

    def _make_l3(
        self,
        antipattern_summary,
        adr_summary,
        learning_match,
        graph_snapshot,
        now: datetime,
    ):
        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        return ModelKnowledgeContextBundle(
            repo="omnibase_core",
            ticket_id="OMN-11928",
            architecture_context="Architecture: layered, contract-first.",
            relevant_adrs=(adr_summary,),
            applicable_antipatterns=(antipattern_summary,),
            prior_learnings=(learning_match,),
            dependency_graph=graph_snapshot,
            bundle_level="L3",
            degraded=False,
            degraded_providers=(),
            missing_sections=(),
            bundle_hash="jkl012",
            generated_at=now,
        )

    def test_frozen(self, antipattern_summary, now: datetime) -> None:
        bundle = self._make_l0(antipattern_summary, now)
        with pytest.raises(Exception):
            bundle.repo = "changed"  # type: ignore[misc]

    def test_extra_forbid(self, antipattern_summary, now: datetime) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        with pytest.raises(ValidationError):
            ModelKnowledgeContextBundle(
                repo="omnibase_core",
                ticket_id=None,
                architecture_context="",
                relevant_adrs=(),
                applicable_antipatterns=(antipattern_summary,),
                prior_learnings=(),
                dependency_graph=None,
                bundle_level="L0",
                degraded=False,
                degraded_providers=(),
                missing_sections=(),
                bundle_hash="abc",
                generated_at=now,
                unknown_field="boom",  # type: ignore[call-arg]
            )

    def test_tuple_fields_not_list(self, antipattern_summary, now: datetime) -> None:
        bundle = self._make_l0(antipattern_summary, now)
        assert isinstance(bundle.applicable_antipatterns, tuple)
        assert isinstance(bundle.relevant_adrs, tuple)
        assert isinstance(bundle.prior_learnings, tuple)
        assert isinstance(bundle.degraded_providers, tuple)
        assert isinstance(bundle.missing_sections, tuple)

    def test_to_markdown_l0_contains_antipatterns(
        self, antipattern_summary, now: datetime
    ) -> None:
        bundle = self._make_l0(antipattern_summary, now)
        md = bundle.to_markdown()
        assert "Antipatterns" in md
        assert "no-optional-type" in md
        assert isinstance(md, str)

    def test_to_markdown_l0_no_adrs(self, antipattern_summary, now: datetime) -> None:
        bundle = self._make_l0(antipattern_summary, now)
        md = bundle.to_markdown()
        assert "ADR" not in md

    def test_to_markdown_l1_contains_adrs(
        self, antipattern_summary, adr_summary, now: datetime
    ) -> None:
        bundle = self._make_l1(antipattern_summary, adr_summary, now)
        md = bundle.to_markdown()
        assert "ADR" in md
        assert "ADR-001" in md
        assert "Antipatterns" in md

    def test_to_markdown_l2_contains_architecture(
        self, antipattern_summary, adr_summary, now: datetime
    ) -> None:
        bundle = self._make_l2(antipattern_summary, adr_summary, now)
        md = bundle.to_markdown()
        assert "Architecture" in md
        assert "layered" in md

    def test_to_markdown_l2_capped_at_4000(
        self, antipattern_summary, adr_summary, now: datetime
    ) -> None:
        bundle = self._make_l2(antipattern_summary, adr_summary, now)
        md = bundle.to_markdown()
        assert len(md) <= 4000

    def test_to_markdown_l3_contains_graph_and_learnings(
        self,
        antipattern_summary,
        adr_summary,
        learning_match,
        graph_snapshot,
        now: datetime,
    ) -> None:
        bundle = self._make_l3(
            antipattern_summary, adr_summary, learning_match, graph_snapshot, now
        )
        md = bundle.to_markdown()
        assert "Prior Learnings" in md
        assert "Always use uv run" in md
        assert "Dependency Graph" in md
        assert "omnibase_core depends on omnibase_compat" in md

    def test_degraded_flag_appears_in_markdown(
        self, antipattern_summary, now: datetime
    ) -> None:
        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        bundle = ModelKnowledgeContextBundle(
            repo="omnibase_core",
            ticket_id=None,
            architecture_context="",
            relevant_adrs=(),
            applicable_antipatterns=(antipattern_summary,),
            prior_learnings=(),
            dependency_graph=None,
            bundle_level="L0",
            degraded=True,
            degraded_providers=(EnumKnowledgeProviderKind.CODE_INDEX,),
            missing_sections=("architecture_context",),
            bundle_hash="abc",
            generated_at=now,
        )
        md = bundle.to_markdown()
        assert "degraded" in md.lower() or "DEGRADED" in md

    def test_bundle_level_invalid(self, antipattern_summary, now: datetime) -> None:
        from pydantic import ValidationError

        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        with pytest.raises(ValidationError):
            ModelKnowledgeContextBundle(
                repo="omnibase_core",
                ticket_id=None,
                architecture_context="",
                relevant_adrs=(),
                applicable_antipatterns=(antipattern_summary,),
                prior_learnings=(),
                dependency_graph=None,
                bundle_level="L9",  # type: ignore[arg-type]
                degraded=False,
                degraded_providers=(),
                missing_sections=(),
                bundle_hash="abc",
                generated_at=now,
            )


class TestGenericProviderDiscriminator:
    """OMN-18372 — the provider surface carries no vendor in its type."""

    def test_enum_values_name_no_vendor(self) -> None:
        """Every member names a CLASS of backend, not a product."""
        for kind in EnumKnowledgeProviderKind:
            assert kind.value.islower()
            assert kind.value.replace("_", "").isalpha()

    def test_bundle_round_trips_with_degraded_providers(
        self, antipattern_summary, now: datetime
    ) -> None:
        """AC2 — a degraded bundle round-trips through model_validate/model_dump."""
        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        original = ModelKnowledgeContextBundle(
            repo="omnibase_core",
            ticket_id="OMN-18372",
            architecture_context="",
            relevant_adrs=(),
            applicable_antipatterns=(antipattern_summary,),
            prior_learnings=(),
            dependency_graph=None,
            bundle_level="L0",
            degraded=True,
            degraded_providers=(
                EnumKnowledgeProviderKind.CODE_INDEX,
                EnumKnowledgeProviderKind.DEPENDENCY_GRAPH,
            ),
            missing_sections=("architecture_context",),
            bundle_hash="abc",
            generated_at=now,
        )
        restored = ModelKnowledgeContextBundle.model_validate(original.model_dump())
        assert restored == original
        assert restored.degraded_providers == (
            EnumKnowledgeProviderKind.CODE_INDEX,
            EnumKnowledgeProviderKind.DEPENDENCY_GRAPH,
        )

    def test_degraded_providers_rejects_free_text(
        self, antipattern_summary, now: datetime
    ) -> None:
        """A failed backend is recorded by kind, never by a vendor string."""
        from pydantic import ValidationError

        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        with pytest.raises(ValidationError):
            ModelKnowledgeContextBundle(
                repo="omnibase_core",
                ticket_id=None,
                architecture_context="",
                relevant_adrs=(),
                applicable_antipatterns=(antipattern_summary,),
                prior_learnings=(),
                dependency_graph=None,
                bundle_level="L0",
                degraded=True,
                degraded_providers=("some_vendor_product",),  # type: ignore[arg-type]
                missing_sections=(),
                bundle_hash="abc",
                generated_at=now,
            )

    def test_degraded_markdown_names_the_provider_kinds(
        self, antipattern_summary, now: datetime
    ) -> None:
        """to_markdown renders the generic kind values, not enum reprs."""
        from omnibase_core.models.context.model_knowledge_context_bundle import (
            ModelKnowledgeContextBundle,
        )

        bundle = ModelKnowledgeContextBundle(
            repo="omnibase_core",
            ticket_id=None,
            architecture_context="",
            relevant_adrs=(),
            applicable_antipatterns=(antipattern_summary,),
            prior_learnings=(),
            dependency_graph=None,
            bundle_level="L0",
            degraded=True,
            degraded_providers=(EnumKnowledgeProviderKind.CODE_INDEX,),
            missing_sections=("architecture_context",),
            bundle_hash="abc",
            generated_at=now,
        )
        md = bundle.to_markdown()
        assert "code_index" in md
        assert "EnumKnowledgeProviderKind" not in md
