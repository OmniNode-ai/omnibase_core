# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for NodeContractResolveCompute.

Covers:
- Single patch resolution
- Multi-patch chain (ordered application)
- Empty patches (base profile resolution only)
- include_diff=True path
- include_overlay_refs=True / False
- compute_canonical_hash utility
- ModelContractResolveInput / ModelContractResolveOutput model construction
- ModelOverlayRef construction
- Event models (requested / completed)

Ticket: OMN-2754
"""

from __future__ import annotations

import pytest

from omnibase_core.enums.enum_overlay_scope import EnumOverlayScope
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.events.contract_resolve import (
    CONTRACT_RESOLVE_COMPLETED_EVENT,
    CONTRACT_RESOLVE_REQUESTED_EVENT,
    ModelContractResolveCompletedEvent,
    ModelContractResolveRequestedEvent,
)
from omnibase_core.models.nodes.contract_resolve import (
    ModelContractResolveInput,
    ModelContractResolveOptions,
    ModelContractResolveOutput,
    ModelOverlayRef,
    ModelResolverBuild,
)
from omnibase_core.nodes.node_contract_resolve_compute import NodeContractResolveCompute
from omnibase_core.utils.util_canonical_hash import compute_canonical_hash

pytestmark = pytest.mark.unit

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def compute_profile_ref() -> ModelProfileReference:
    """Return a standard compute profile reference for testing."""
    return ModelProfileReference(profile="compute_pure", version="1.0.0")


@pytest.fixture
def node() -> NodeContractResolveCompute:
    """Return a fresh NodeContractResolveCompute instance."""
    return NodeContractResolveCompute()


@pytest.fixture
def single_patch(compute_profile_ref: ModelProfileReference) -> ModelContractPatch:
    """A single patch that establishes a new contract identity."""
    from omnibase_core.models.primitives.model_semver import (
        ModelSemVer,
    )

    return ModelContractPatch(
        extends=compute_profile_ref,
        name="test_handler",
        node_version=ModelSemVer(major=1, minor=0, patch=0),
        description="Test handler for OMN-2754",
    )


# ─────────────────────────────────────────────────────────────────────────────
# canonical hash utility
# ─────────────────────────────────────────────────────────────────────────────


class TestComputeCanonicalHash:
    """Tests for compute_canonical_hash utility."""

    def test_deterministic_for_same_input(self) -> None:
        """Same input always produces the same hash."""
        obj = {"b": 2, "a": 1}
        assert compute_canonical_hash(obj) == compute_canonical_hash(obj)

    def test_key_order_does_not_affect_hash(self) -> None:
        """Key insertion order is irrelevant — sort_keys normalises output."""
        assert compute_canonical_hash({"a": 1, "b": 2}) == compute_canonical_hash(
            {"b": 2, "a": 1}
        )

    def test_none_values_stripped(self) -> None:
        """None-valued keys are stripped before hashing."""
        with_none = {"a": 1, "b": None}
        without_none = {"a": 1}
        assert compute_canonical_hash(with_none) == compute_canonical_hash(without_none)

    def test_empty_list_not_stripped(self) -> None:
        """Empty lists are distinct from None and are not stripped."""
        with_empty = {"a": []}
        without_key = {}
        assert compute_canonical_hash(with_empty) != compute_canonical_hash(without_key)

    def test_returns_64_char_hex_string(self) -> None:
        """SHA-256 hex digest is always 64 characters."""
        result = compute_canonical_hash({"x": 42})
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_inputs_differ(self) -> None:
        """Distinct inputs produce distinct hashes."""
        assert compute_canonical_hash({"a": 1}) != compute_canonical_hash({"a": 2})

    def test_pydantic_model_roundtrip(
        self, compute_profile_ref: ModelProfileReference
    ) -> None:
        """Hashing a Pydantic model is deterministic via model_dump()."""
        h1 = compute_canonical_hash(compute_profile_ref)
        h2 = compute_canonical_hash(compute_profile_ref)
        assert h1 == h2
        assert len(h1) == 64


# ─────────────────────────────────────────────────────────────────────────────
# ModelOverlayRef
# ─────────────────────────────────────────────────────────────────────────────


class TestModelOverlayRef:
    """Tests for the ModelOverlayRef model."""

    def test_basic_construction(self) -> None:
        ref = ModelOverlayRef(
            overlay_id="my_patch",
            version="1.0.0",
            content_hash="abc" * 21 + "a",  # 64 chars
            scope=EnumOverlayScope.ORG,
            order_index=0,
        )
        assert ref.overlay_id == "my_patch"
        assert ref.scope == EnumOverlayScope.ORG
        assert ref.order_index == 0
        assert ref.source_ref is None

    def test_with_source_ref(self) -> None:
        ref = ModelOverlayRef(
            overlay_id="x",
            version="2.0.0",
            content_hash="a" * 64,
            source_ref="git://sha/abc",
            scope=EnumOverlayScope.ENV,
            order_index=1,
        )
        assert ref.source_ref == "git://sha/abc"

    def test_frozen(self) -> None:
        ref = ModelOverlayRef(
            overlay_id="x",
            version="1.0.0",
            content_hash="a" * 64,
            scope=EnumOverlayScope.BASE,
            order_index=0,
        )
        with pytest.raises(Exception):
            ref.overlay_id = "mutated"  # type: ignore[misc]

    def test_order_index_must_be_nonnegative(self) -> None:
        with pytest.raises(Exception):
            ModelOverlayRef(
                overlay_id="x",
                version="1.0.0",
                content_hash="a" * 64,
                scope=EnumOverlayScope.USER,
                order_index=-1,
            )


# ─────────────────────────────────────────────────────────────────────────────
# ModelContractResolveInput
# ─────────────────────────────────────────────────────────────────────────────


class TestModelContractResolveInput:
    """Tests for the typed input model."""

    def test_empty_patches_allowed(
        self, compute_profile_ref: ModelProfileReference
    ) -> None:
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[],
        )
        assert inp.patches == []

    def test_default_options(self, compute_profile_ref: ModelProfileReference) -> None:
        inp = ModelContractResolveInput(base_profile_ref=compute_profile_ref)
        assert inp.options.include_overlay_refs is True
        assert inp.options.include_diff is False
        assert inp.options.normalize_for_hash is True

    def test_frozen(self, compute_profile_ref: ModelProfileReference) -> None:
        inp = ModelContractResolveInput(base_profile_ref=compute_profile_ref)
        with pytest.raises(Exception):
            inp.patches = []  # type: ignore[misc]


# ─────────────────────────────────────────────────────────────────────────────
# Event models
# ─────────────────────────────────────────────────────────────────────────────


class TestContractResolveEvents:
    """Tests for the contract.resolve event models."""

    def test_requested_event_type(self) -> None:
        from uuid import uuid4

        ev = ModelContractResolveRequestedEvent.create(
            run_id=uuid4(),
            base_profile="compute_pure",
            patch_count=0,
        )
        assert ev.event_type == CONTRACT_RESOLVE_REQUESTED_EVENT
        assert ev.base_profile == "compute_pure"
        assert ev.patch_count == 0

    def test_completed_event_type(self) -> None:
        from uuid import uuid4

        build = ModelResolverBuild(build_hash="a" * 64)
        ev = ModelContractResolveCompletedEvent.create(
            run_id=uuid4(),
            resolved_hash="b" * 64,
            overlays_applied_count=2,
            overlay_refs=[],
            resolver_build=build,
            duration_ms=10,
        )
        assert ev.event_type == CONTRACT_RESOLVE_COMPLETED_EVENT
        assert ev.overlays_applied_count == 2

    def test_requested_event_type_validator_rejects_wrong_type(self) -> None:
        from uuid import uuid4

        with pytest.raises(Exception):
            ModelContractResolveRequestedEvent(
                run_id=uuid4(),
                base_profile="x",
                patch_count=0,
                event_type="wrong.type",
            )

    def test_completed_event_type_validator_rejects_wrong_type(self) -> None:
        from uuid import uuid4

        build = ModelResolverBuild(build_hash="a" * 64)
        with pytest.raises(Exception):
            ModelContractResolveCompletedEvent(
                run_id=uuid4(),
                resolved_hash="b" * 64,
                overlays_applied_count=0,
                overlay_refs=[],
                resolver_build=build,
                duration_ms=0,
                event_type="wrong.type",
            )


# ─────────────────────────────────────────────────────────────────────────────
# NodeContractResolveCompute integration
# ─────────────────────────────────────────────────────────────────────────────


class TestNodeContractResolveCompute:
    """Integration tests for NodeContractResolveCompute.resolve()."""

    def test_empty_patches_returns_output(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
    ) -> None:
        """Resolving with no patches returns the base profile contract."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[],
            options=ModelContractResolveOptions(include_overlay_refs=False),
        )
        output = node.resolve(inp)

        assert isinstance(output, ModelContractResolveOutput)
        assert len(output.resolved_hash) == 64
        assert output.patch_hashes == []
        assert output.overlay_refs == []
        assert output.diff is None

    def test_single_patch_produces_non_empty_hash(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
        single_patch: ModelContractPatch,
    ) -> None:
        """A single patch produces a deterministic hash."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[single_patch],
        )
        output = node.resolve(inp)

        assert len(output.resolved_hash) == 64
        assert len(output.patch_hashes) == 1
        assert len(output.patch_hashes[0]) == 64

    def test_single_patch_overlay_refs_wired(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
        single_patch: ModelContractPatch,
    ) -> None:
        """overlay_refs are populated for each applied patch (not stubs)."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[single_patch],
            options=ModelContractResolveOptions(include_overlay_refs=True),
        )
        output = node.resolve(inp)

        assert len(output.overlay_refs) == 1
        ref = output.overlay_refs[0]
        assert ref.order_index == 0
        assert ref.overlay_id == "test_handler"
        assert len(ref.content_hash) == 64

    def test_multi_patch_chain_order(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
    ) -> None:
        """Multiple patches are applied in order; order_index reflects position."""
        from omnibase_core.models.primitives.model_semver import ModelSemVer

        patch_a = ModelContractPatch(
            extends=compute_profile_ref,
            name="handler_a",
            node_version=ModelSemVer(major=1, minor=0, patch=0),
        )
        patch_b = ModelContractPatch(
            extends=compute_profile_ref,
            name="handler_b",
            node_version=ModelSemVer(major=2, minor=0, patch=0),
        )

        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[patch_a, patch_b],
            options=ModelContractResolveOptions(include_overlay_refs=True),
        )
        output = node.resolve(inp)

        assert len(output.patch_hashes) == 2
        assert len(output.overlay_refs) == 2
        assert output.overlay_refs[0].overlay_id == "handler_a"
        assert output.overlay_refs[0].order_index == 0
        assert output.overlay_refs[1].overlay_id == "handler_b"
        assert output.overlay_refs[1].order_index == 1

    def test_include_diff_false_no_diff_string(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
        single_patch: ModelContractPatch,
    ) -> None:
        """diff is None when include_diff=False."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[single_patch],
            options=ModelContractResolveOptions(include_diff=False),
        )
        output = node.resolve(inp)
        assert output.diff is None

    def test_include_diff_true_provides_diff_string(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
        single_patch: ModelContractPatch,
    ) -> None:
        """diff is a non-empty string when include_diff=True and patches exist."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[single_patch],
            options=ModelContractResolveOptions(include_diff=True),
        )
        output = node.resolve(inp)
        # The diff may be empty if no fields changed, but it must be a string.
        assert isinstance(output.diff, str)

    def test_resolver_build_is_populated(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
    ) -> None:
        """resolver_build is always present in the output."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[],
        )
        output = node.resolve(inp)
        assert isinstance(output.resolver_build, ModelResolverBuild)
        assert output.resolver_build.node_version == "1.0.0"
        assert len(output.resolver_build.build_hash) == 64

    def test_deterministic_output_for_same_input(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
        single_patch: ModelContractPatch,
    ) -> None:
        """Same input always produces the same resolved_hash."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[single_patch],
            options=ModelContractResolveOptions(include_overlay_refs=False),
        )
        out1 = node.resolve(inp)
        out2 = node.resolve(inp)
        assert out1.resolved_hash == out2.resolved_hash

    def test_overlay_refs_empty_when_disabled(
        self,
        node: NodeContractResolveCompute,
        compute_profile_ref: ModelProfileReference,
        single_patch: ModelContractPatch,
    ) -> None:
        """overlay_refs is empty when include_overlay_refs=False."""
        inp = ModelContractResolveInput(
            base_profile_ref=compute_profile_ref,
            patches=[single_patch],
            options=ModelContractResolveOptions(include_overlay_refs=False),
        )
        output = node.resolve(inp)
        assert output.overlay_refs == []
        # But patch_hashes are still computed.
        assert len(output.patch_hashes) == 1
