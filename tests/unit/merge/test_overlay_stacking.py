# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for the overlay stacking pipeline (OMN-2757).

Tests cover:
- Single overlay application
- Two overlays applied in sequence (org + user scope)
- Scope ordering validation (auto-sort and strict mode)
- overlay_refs populated correctly in merge-completed events
- overlays_applied_count accuracy
- Resolved contract reflects all patches in correct order

.. versionadded:: 0.18.0
    Added as part of overlay stacking pipeline (OMN-2757)
"""

from unittest.mock import Mock

import pytest

from omnibase_core.enums.enum_overlay_scope import SCOPE_ORDER, EnumOverlayScope
from omnibase_core.models.contracts.model_contract_patch import ModelContractPatch
from omnibase_core.models.contracts.model_profile_reference import ModelProfileReference
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.merge.model_overlay_ref import ModelOverlayRef
from omnibase_core.models.merge.model_overlay_stack_entry import ModelOverlayStackEntry
from omnibase_core.models.primitives.model_semver import ModelSemVer

pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def profile_reference() -> ModelProfileReference:
    """Standard profile reference for tests."""
    return ModelProfileReference(profile="compute_pure", version="1.0.0")


@pytest.fixture
def base_semver() -> ModelSemVer:
    """Base version for patches."""
    return ModelSemVer(major=1, minor=0, patch=0)


@pytest.fixture
def mock_base_contract() -> Mock:
    """
    Mock ModelContractBase returned by the profile factory.

    Uses .behavior (not .descriptor) to match ModelContractBase field name.
    """
    mock = Mock()
    mock.name = "base_contract"
    mock.contract_version = ModelSemVer(major=0, minor=1, patch=0)
    mock.description = "Base contract"
    mock.input_model = "BaseInput"
    mock.output_model = "BaseOutput"
    mock.behavior = None
    mock.tags = []
    return mock


@pytest.fixture
def mock_profile_factory(mock_base_contract: Mock) -> Mock:
    """Mock profile factory that returns the base contract mock."""
    factory = Mock()
    factory.get_profile = Mock(return_value=mock_base_contract)
    return factory


@pytest.fixture
def base_patch(
    profile_reference: ModelProfileReference, base_semver: ModelSemVer
) -> ModelContractPatch:
    """Base contract patch defining a new contract identity."""
    return ModelContractPatch(
        extends=profile_reference,
        name="my_handler",
        node_version=base_semver,
        description="Base description",
    )


@pytest.fixture
def org_patch(profile_reference: ModelProfileReference) -> ModelContractPatch:
    """Overlay patch representing organisation-level overrides."""
    return ModelContractPatch(
        extends=profile_reference,
        description="Org override description",
    )


@pytest.fixture
def user_patch(profile_reference: ModelProfileReference) -> ModelContractPatch:
    """Overlay patch representing user-level overrides."""
    return ModelContractPatch(
        extends=profile_reference,
        description="User override description",
    )


def make_entry(
    overlay_id: str,
    patch: ModelContractPatch,
    scope: EnumOverlayScope,
    version: str = "1.0.0",
) -> ModelOverlayStackEntry:
    """Helper: build a ModelOverlayStackEntry."""
    return ModelOverlayStackEntry(
        overlay_id=overlay_id,
        overlay_patch=patch,
        scope=scope,
        version=version,
    )


def make_engine(factory: Mock) -> object:
    """Import and build a ContractMergeEngine (deferred import avoids cycle)."""
    from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

    return ContractMergeEngine(factory)


# =============================================================================
# EnumOverlayScope
# =============================================================================


class TestEnumOverlayScope:
    """Verify EnumOverlayScope values and ordering."""

    def test_all_six_scopes_defined(self) -> None:
        """EnumOverlayScope must define exactly 6 scopes."""
        scopes = list(EnumOverlayScope)
        assert len(scopes) == 6

    def test_scope_values_are_strings(self) -> None:
        """Each scope value must be a lowercase string."""
        for scope in EnumOverlayScope:
            assert isinstance(scope.value, str)
            assert scope.value == scope.value.lower()

    def test_canonical_ordering(self) -> None:
        """SCOPE_ORDER must encode BASE < ORG < PROJECT < ENV < USER < SESSION."""
        assert SCOPE_ORDER[EnumOverlayScope.BASE] < SCOPE_ORDER[EnumOverlayScope.ORG]
        assert SCOPE_ORDER[EnumOverlayScope.ORG] < SCOPE_ORDER[EnumOverlayScope.PROJECT]
        assert SCOPE_ORDER[EnumOverlayScope.PROJECT] < SCOPE_ORDER[EnumOverlayScope.ENV]
        assert SCOPE_ORDER[EnumOverlayScope.ENV] < SCOPE_ORDER[EnumOverlayScope.USER]
        assert (
            SCOPE_ORDER[EnumOverlayScope.USER] < SCOPE_ORDER[EnumOverlayScope.SESSION]
        )

    def test_scope_string_representation(self) -> None:
        """str() of a scope must match its value."""
        assert str(EnumOverlayScope.BASE) == "base"
        assert str(EnumOverlayScope.SESSION) == "session"

    def test_scope_repr(self) -> None:
        """repr() must include the enum class name."""
        assert repr(EnumOverlayScope.PROJECT) == "EnumOverlayScope.PROJECT"


# =============================================================================
# ModelOverlayRef
# =============================================================================


class TestModelOverlayRef:
    """Verify ModelOverlayRef model behaviour."""

    def test_basic_construction(self) -> None:
        """ModelOverlayRef can be constructed with required fields."""
        ref = ModelOverlayRef(
            overlay_id="org-defaults",
            version="1.2.0",
            scope=EnumOverlayScope.ORG,
            order_index=0,
        )
        assert ref.overlay_id == "org-defaults"
        assert ref.version == "1.2.0"
        assert ref.scope == EnumOverlayScope.ORG
        assert ref.order_index == 0
        assert ref.content_hash is None

    def test_with_content_hash(self) -> None:
        """ModelOverlayRef accepts an optional content_hash."""
        ref = ModelOverlayRef(
            overlay_id="user-prefs",
            version="2.0.0",
            content_hash="sha256:abc123",
            scope=EnumOverlayScope.USER,
            order_index=1,
        )
        assert ref.content_hash == "sha256:abc123"

    def test_immutable(self) -> None:
        """ModelOverlayRef is frozen — assignment must raise."""
        ref = ModelOverlayRef(
            overlay_id="x",
            version="1.0.0",
            scope=EnumOverlayScope.BASE,
            order_index=0,
        )
        with pytest.raises((AttributeError, TypeError, ValueError)):
            ref.overlay_id = "y"  # type: ignore[misc]

    def test_order_index_non_negative(self) -> None:
        """order_index must be >= 0."""
        with pytest.raises(Exception):
            ModelOverlayRef(
                overlay_id="x",
                version="1.0.0",
                scope=EnumOverlayScope.BASE,
                order_index=-1,
            )


# =============================================================================
# ModelOverlayStackEntry
# =============================================================================


class TestModelOverlayStackEntry:
    """Verify ModelOverlayStackEntry model behaviour."""

    def test_basic_construction(
        self,
        profile_reference: ModelProfileReference,
    ) -> None:
        """ModelOverlayStackEntry can be constructed with required fields."""
        patch = ModelContractPatch(extends=profile_reference, description="override")
        entry = ModelOverlayStackEntry(
            overlay_id="my-overlay",
            overlay_patch=patch,
            scope=EnumOverlayScope.PROJECT,
            version="1.0.0",
        )
        assert entry.overlay_id == "my-overlay"
        assert entry.scope == EnumOverlayScope.PROJECT
        assert entry.source_ref is None

    def test_default_version(
        self,
        profile_reference: ModelProfileReference,
    ) -> None:
        """version defaults to '1.0.0'."""
        patch = ModelContractPatch(extends=profile_reference)
        entry = ModelOverlayStackEntry(
            overlay_id="x",
            overlay_patch=patch,
            scope=EnumOverlayScope.ENV,
        )
        assert entry.version == "1.0.0"


# =============================================================================
# Single overlay application
# =============================================================================


class TestSingleOverlay:
    """merge_with_overlays with a single overlay entry."""

    def test_single_overlay_applies_description(
        self,
        mock_profile_factory: Mock,
        mock_base_contract: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
    ) -> None:
        """A single overlay must override the description on the merged contract."""
        engine = make_engine(mock_profile_factory)
        entry = make_entry("org-defaults", org_patch, EnumOverlayScope.ORG)

        result = engine.merge_with_overlays(base_patch, [entry])  # type: ignore[attr-defined]

        assert result.description == "Org override description"

    def test_single_overlay_preserves_name(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
    ) -> None:
        """A single overlay that doesn't touch name must preserve base name."""
        engine = make_engine(mock_profile_factory)
        entry = make_entry("org-defaults", org_patch, EnumOverlayScope.ORG)

        result = engine.merge_with_overlays(base_patch, [entry])  # type: ignore[attr-defined]

        assert result.name == "my_handler"

    def test_empty_overlay_list_equivalent_to_merge(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
    ) -> None:
        """merge_with_overlays([]) must produce the same contract as merge()."""
        engine = make_engine(mock_profile_factory)

        plain_result = engine.merge(base_patch)  # type: ignore[attr-defined]
        overlay_result = engine.merge_with_overlays(base_patch, [])  # type: ignore[attr-defined]

        assert plain_result.name == overlay_result.name
        assert plain_result.description == overlay_result.description
        assert plain_result.input_model == overlay_result.input_model


# =============================================================================
# Two overlays — org then user
# =============================================================================


class TestTwoOverlays:
    """merge_with_overlays with two overlays (org + user)."""

    def test_user_scope_wins_over_org_scope(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
        user_patch: ModelContractPatch,
    ) -> None:
        """When org and user overlays both set description, user wins (higher scope)."""
        engine = make_engine(mock_profile_factory)
        stack = [
            make_entry("org-defaults", org_patch, EnumOverlayScope.ORG),
            make_entry("user-prefs", user_patch, EnumOverlayScope.USER),
        ]

        result = engine.merge_with_overlays(base_patch, stack)  # type: ignore[attr-defined]

        assert result.description == "User override description"


# =============================================================================
# overlay_refs and overlays_applied_count wiring
# =============================================================================


class TestOverlayRefWiring:
    """Verify overlay_refs and overlays_applied_count are wired into emitted events."""

    def test_overlay_refs_count_in_completed_event(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
        user_patch: ModelContractPatch,
    ) -> None:
        """merge_completed event must have overlays_applied_count == len(stack)."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        captured: list[object] = []
        mock_emitter = Mock()
        mock_emitter.emit_merge_completed = Mock(
            side_effect=lambda e: captured.append(e)
        )
        mock_emitter.emit_merge_started = Mock()

        engine = ContractMergeEngine(mock_profile_factory, event_emitter=mock_emitter)
        stack = [
            make_entry("org-defaults", org_patch, EnumOverlayScope.ORG),
            make_entry("user-prefs", user_patch, EnumOverlayScope.USER),
        ]
        engine.merge_with_overlays(base_patch, stack)

        assert len(captured) == 1
        completed = captured[0]
        assert completed.overlays_applied_count == 2  # type: ignore[attr-defined]

    def test_overlay_refs_populated_in_completed_event(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
        user_patch: ModelContractPatch,
    ) -> None:
        """overlay_refs in merge_completed event must record id, scope, and order_index."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        captured: list[object] = []
        mock_emitter = Mock()
        mock_emitter.emit_merge_completed = Mock(
            side_effect=lambda e: captured.append(e)
        )
        mock_emitter.emit_merge_started = Mock()

        engine = ContractMergeEngine(mock_profile_factory, event_emitter=mock_emitter)
        stack = [
            make_entry("org-defaults", org_patch, EnumOverlayScope.ORG, "1.0.0"),
            make_entry("user-prefs", user_patch, EnumOverlayScope.USER, "2.1.0"),
        ]
        engine.merge_with_overlays(base_patch, stack)

        completed = captured[0]
        refs = completed.overlay_refs  # type: ignore[attr-defined]
        assert len(refs) == 2

        assert refs[0].overlay_id == "org-defaults"
        assert refs[0].scope == EnumOverlayScope.ORG
        assert refs[0].order_index == 0
        assert refs[0].version == "1.0.0"

        assert refs[1].overlay_id == "user-prefs"
        assert refs[1].scope == EnumOverlayScope.USER
        assert refs[1].order_index == 1
        assert refs[1].version == "2.1.0"

    def test_no_overlays_applied_count_is_zero(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
    ) -> None:
        """When merge() is called with no overlays, overlays_applied_count must be 0."""
        from omnibase_core.merge.contract_merge_engine import ContractMergeEngine

        captured: list[object] = []
        mock_emitter = Mock()
        mock_emitter.emit_merge_completed = Mock(
            side_effect=lambda e: captured.append(e)
        )
        mock_emitter.emit_merge_started = Mock()

        engine = ContractMergeEngine(mock_profile_factory, event_emitter=mock_emitter)
        engine.merge(base_patch)

        completed = captured[0]
        assert completed.overlays_applied_count == 0  # type: ignore[attr-defined]
        assert completed.overlay_refs == []  # type: ignore[attr-defined]


# =============================================================================
# Scope ordering validation
# =============================================================================


class TestScopeOrdering:
    """Tests for overlay scope ordering: auto-sort and strict_ordering mode."""

    def test_out_of_order_sorts_automatically(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
        user_patch: ModelContractPatch,
    ) -> None:
        """Out-of-order overlays are auto-sorted to canonical scope order by default."""
        engine = make_engine(mock_profile_factory)
        # Deliberately supply user before org — should be auto-sorted
        stack = [
            make_entry("user-prefs", user_patch, EnumOverlayScope.USER),
            make_entry("org-defaults", org_patch, EnumOverlayScope.ORG),
        ]

        # Should not raise — result must reflect org then user (user wins)
        result = engine.merge_with_overlays(base_patch, stack)  # type: ignore[attr-defined]
        assert result.description == "User override description"

    def test_out_of_order_raises_in_strict_mode(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
        user_patch: ModelContractPatch,
    ) -> None:
        """strict_ordering=True raises ModelOnexError when overlays are out of order."""
        engine = make_engine(mock_profile_factory)
        stack = [
            make_entry("user-prefs", user_patch, EnumOverlayScope.USER),
            make_entry("org-defaults", org_patch, EnumOverlayScope.ORG),
        ]

        with pytest.raises(ModelOnexError):
            engine.merge_with_overlays(  # type: ignore[attr-defined]
                base_patch, stack, strict_ordering=True
            )

    def test_canonical_order_does_not_raise_in_strict_mode(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
        user_patch: ModelContractPatch,
    ) -> None:
        """Overlays already in canonical order must not raise in strict_ordering mode."""
        engine = make_engine(mock_profile_factory)
        stack = [
            make_entry("org-defaults", org_patch, EnumOverlayScope.ORG),
            make_entry("user-prefs", user_patch, EnumOverlayScope.USER),
        ]

        # No exception expected
        result = engine.merge_with_overlays(  # type: ignore[attr-defined]
            base_patch, stack, strict_ordering=True
        )
        assert result.name == "my_handler"

    def test_same_scope_level_allowed(
        self,
        mock_profile_factory: Mock,
        base_patch: ModelContractPatch,
        org_patch: ModelContractPatch,
    ) -> None:
        """Two overlays with the same scope level are permitted (not a violation)."""
        engine = make_engine(mock_profile_factory)
        org_patch2 = ModelContractPatch(
            extends=ModelProfileReference(profile="compute_pure", version="1.0.0"),
            description="Org override 2",
        )
        stack = [
            make_entry("org-a", org_patch, EnumOverlayScope.ORG),
            make_entry("org-b", org_patch2, EnumOverlayScope.ORG),
        ]

        # Same scope is not out of order — must not raise
        result = engine.merge_with_overlays(  # type: ignore[attr-defined]
            base_patch, stack, strict_ordering=True
        )
        assert result.description == "Org override 2"
