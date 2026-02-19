# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Comprehensive unit tests for interface definition models (OMN-1968).

Tests cover:
- E1: EnumInterfaceKind - all values, str(), uniqueness
- E2: EnumMockStrategy - all values, str(), uniqueness
- E3: EnumDefinitionFormat - all values, str(), uniqueness
- E4: EnumInterfaceSurface - all values, str(), uniqueness
- E5: EnumDefinitionLocation - all values, str(), uniqueness
- M1: ModelInterfaceProvided - construction, immutability, extra fields, validation,
      cross-field validation (file_ref requires definition_ref)
- M2: ModelInterfaceConsumed - construction, immutability, extra fields, validation
- RT: YAML round-trip serialization for both models
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.ticket.enum_definition_format import EnumDefinitionFormat
from omnibase_core.enums.ticket.enum_definition_location import EnumDefinitionLocation
from omnibase_core.enums.ticket.enum_interface_kind import EnumInterfaceKind
from omnibase_core.enums.ticket.enum_interface_surface import EnumInterfaceSurface
from omnibase_core.enums.ticket.enum_mock_strategy import EnumMockStrategy
from omnibase_core.models.ticket.model_interface_consumed import (
    ModelInterfaceConsumed,
)
from omnibase_core.models.ticket.model_interface_provided import (
    ModelInterfaceProvided,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def provided_interface() -> ModelInterfaceProvided:
    """Create a minimal ModelInterfaceProvided for testing."""
    return ModelInterfaceProvided(
        id="iface-001",
        name="ProtocolRuntimeEntryPoint",
        kind=EnumInterfaceKind.PROTOCOL,
        surface=EnumInterfaceSurface.PUBLIC_API,
        definition_format=EnumDefinitionFormat.PYTHON,
        definition="class ProtocolRuntimeEntryPoint(Protocol): ...",
    )


@pytest.fixture
def consumed_interface() -> ModelInterfaceConsumed:
    """Create a minimal ModelInterfaceConsumed for testing."""
    return ModelInterfaceConsumed(
        id="consume-001",
        name="ProtocolEventBus",
        kind=EnumInterfaceKind.PROTOCOL,
        mock_strategy=EnumMockStrategy.PROTOCOL_STUB,
    )


@pytest.fixture
def full_provided_interface() -> ModelInterfaceProvided:
    """Create a ModelInterfaceProvided with all fields populated."""
    return ModelInterfaceProvided(
        id="iface-full",
        name="ModelUserEvent",
        kind=EnumInterfaceKind.EVENT_SCHEMA,
        surface=EnumInterfaceSurface.EVENT_SCHEMA,
        definition_format=EnumDefinitionFormat.YAML,
        definition="type: object\nproperties:\n  user_id: {type: string}",
        definition_hash="abc123def456",
        definition_location=EnumDefinitionLocation.FILE_REF,
        definition_ref="src/models/events.py:ModelUserEvent",
        intended_module_path="omnibase_core.models.events",
        version="1.2.0",
    )


@pytest.fixture
def full_consumed_interface() -> ModelInterfaceConsumed:
    """Create a ModelInterfaceConsumed with all fields populated."""
    return ModelInterfaceConsumed(
        id="consume-full",
        name="ProtocolLogger",
        kind=EnumInterfaceKind.PROTOCOL,
        source_ticket="OMN-1937",
        mock_strategy=EnumMockStrategy.IN_MEMORY,
        required=False,
    )


# =============================================================================
# E1: EnumInterfaceKind Tests
# =============================================================================


@pytest.mark.unit
class TestEnumInterfaceKind:
    """Test EnumInterfaceKind enum values and behavior."""

    def test_has_all_seven_values(self):
        """EnumInterfaceKind has exactly 7 members."""
        assert len(EnumInterfaceKind) == 7

    def test_expected_values(self):
        """Each member has the expected string value."""
        assert EnumInterfaceKind.PROTOCOL.value == "protocol"
        assert EnumInterfaceKind.EVENT_SCHEMA.value == "event_schema"
        assert EnumInterfaceKind.DATA_MODEL.value == "data_model"
        assert EnumInterfaceKind.REST_ENDPOINT.value == "rest_endpoint"
        assert EnumInterfaceKind.DATABASE_SCHEMA.value == "database_schema"
        assert EnumInterfaceKind.CONFIG_SCHEMA.value == "config_schema"
        assert EnumInterfaceKind.CLI_INTERFACE.value == "cli_interface"

    def test_str_returns_value(self):
        """str() on each member returns its string value."""
        for member in EnumInterfaceKind:
            assert str(member) == member.value

    def test_is_str_subclass(self):
        """EnumInterfaceKind members are str instances for JSON serialization."""
        for member in EnumInterfaceKind:
            assert isinstance(member, str)

    def test_values_are_unique(self):
        """All values are unique (enforced by @unique decorator)."""
        values = [m.value for m in EnumInterfaceKind]
        assert len(values) == len(set(values))


# =============================================================================
# E2: EnumMockStrategy Tests
# =============================================================================


@pytest.mark.unit
class TestEnumMockStrategy:
    """Test EnumMockStrategy enum values and behavior."""

    def test_has_all_four_values(self):
        """EnumMockStrategy has exactly 4 members."""
        assert len(EnumMockStrategy) == 4

    def test_expected_values(self):
        """Each member has the expected string value."""
        assert EnumMockStrategy.PROTOCOL_STUB.value == "protocol_stub"
        assert EnumMockStrategy.FIXTURE_DATA.value == "fixture_data"
        assert EnumMockStrategy.IN_MEMORY.value == "in_memory"
        assert EnumMockStrategy.NONE.value == "none"

    def test_str_returns_value(self):
        """str() on each member returns its string value."""
        for member in EnumMockStrategy:
            assert str(member) == member.value

    def test_is_str_subclass(self):
        """EnumMockStrategy members are str instances for JSON serialization."""
        for member in EnumMockStrategy:
            assert isinstance(member, str)

    def test_values_are_unique(self):
        """All values are unique (enforced by @unique decorator)."""
        values = [m.value for m in EnumMockStrategy]
        assert len(values) == len(set(values))


# =============================================================================
# E3: EnumDefinitionFormat Tests
# =============================================================================


@pytest.mark.unit
class TestEnumDefinitionFormat:
    """Test EnumDefinitionFormat enum values and behavior."""

    def test_has_all_five_values(self):
        """EnumDefinitionFormat has exactly 5 members."""
        assert len(EnumDefinitionFormat) == 5

    def test_expected_values(self):
        """Each member has the expected string value."""
        assert EnumDefinitionFormat.PYTHON.value == "python"
        assert EnumDefinitionFormat.YAML.value == "yaml"
        assert EnumDefinitionFormat.JSON.value == "json"
        assert EnumDefinitionFormat.PROTO.value == "proto"
        assert EnumDefinitionFormat.MARKDOWN.value == "markdown"

    def test_str_returns_value(self):
        """str() on each member returns its string value."""
        for member in EnumDefinitionFormat:
            assert str(member) == member.value

    def test_is_str_subclass(self):
        """EnumDefinitionFormat members are str instances for JSON serialization."""
        for member in EnumDefinitionFormat:
            assert isinstance(member, str)

    def test_values_are_unique(self):
        """All values are unique (enforced by @unique decorator)."""
        values = [m.value for m in EnumDefinitionFormat]
        assert len(values) == len(set(values))


# =============================================================================
# E4: EnumInterfaceSurface Tests
# =============================================================================


@pytest.mark.unit
class TestEnumInterfaceSurface:
    """Test EnumInterfaceSurface enum values and behavior."""

    def test_has_all_six_values(self):
        """EnumInterfaceSurface has exactly 6 members."""
        assert len(EnumInterfaceSurface) == 6

    def test_expected_values(self):
        """Each member has the expected string value."""
        assert EnumInterfaceSurface.PUBLIC_API.value == "public_api"
        assert EnumInterfaceSurface.INTERNAL_API.value == "internal_api"
        assert EnumInterfaceSurface.EVENT_SCHEMA.value == "event_schema"
        assert EnumInterfaceSurface.SPI.value == "spi"
        assert EnumInterfaceSurface.CLI.value == "cli"
        assert EnumInterfaceSurface.CONTRACT.value == "contract"

    def test_str_returns_value(self):
        """str() on each member returns its string value."""
        for member in EnumInterfaceSurface:
            assert str(member) == member.value

    def test_is_str_subclass(self):
        """EnumInterfaceSurface members are str instances for JSON serialization."""
        for member in EnumInterfaceSurface:
            assert isinstance(member, str)

    def test_values_are_unique(self):
        """All values are unique (enforced by @unique decorator)."""
        values = [m.value for m in EnumInterfaceSurface]
        assert len(values) == len(set(values))


# =============================================================================
# M1: ModelInterfaceProvided Tests
# =============================================================================


@pytest.mark.unit
class TestModelInterfaceProvided:
    """Test ModelInterfaceProvided construction, immutability, and validation."""

    def test_construction_with_required_fields(
        self, provided_interface: ModelInterfaceProvided
    ):
        """ModelInterfaceProvided can be constructed with required fields only."""
        assert provided_interface.id == "iface-001"
        assert provided_interface.name == "ProtocolRuntimeEntryPoint"
        assert provided_interface.kind == EnumInterfaceKind.PROTOCOL
        assert provided_interface.surface == EnumInterfaceSurface.PUBLIC_API
        assert provided_interface.definition_format == EnumDefinitionFormat.PYTHON
        assert (
            provided_interface.definition
            == "class ProtocolRuntimeEntryPoint(Protocol): ..."
        )

    def test_construction_with_all_fields(
        self, full_provided_interface: ModelInterfaceProvided
    ):
        """ModelInterfaceProvided can be constructed with all fields populated."""
        iface = full_provided_interface
        assert iface.id == "iface-full"
        assert iface.name == "ModelUserEvent"
        assert iface.kind == EnumInterfaceKind.EVENT_SCHEMA
        assert iface.surface == EnumInterfaceSurface.EVENT_SCHEMA
        assert iface.definition_format == EnumDefinitionFormat.YAML
        assert "user_id" in iface.definition
        assert iface.definition_hash == "abc123def456"
        assert iface.definition_location == EnumDefinitionLocation.FILE_REF
        assert iface.definition_ref == "src/models/events.py:ModelUserEvent"
        assert iface.intended_module_path == "omnibase_core.models.events"
        assert iface.version == "1.2.0"

    def test_optional_fields_default_to_none(
        self, provided_interface: ModelInterfaceProvided
    ):
        """Optional fields default to None when not specified."""
        assert provided_interface.definition_hash is None
        assert provided_interface.definition_ref is None
        assert provided_interface.intended_module_path is None
        assert provided_interface.version is None

    def test_definition_location_defaults_to_inline(
        self, provided_interface: ModelInterfaceProvided
    ):
        """definition_location defaults to INLINE."""
        assert provided_interface.definition_location == EnumDefinitionLocation.INLINE

    def test_frozen_immutability(self, provided_interface: ModelInterfaceProvided):
        """Frozen model raises ValidationError when mutating a field."""
        with pytest.raises(ValidationError):
            provided_interface.name = "Modified"  # type: ignore[misc]

    def test_frozen_immutability_all_required_fields(
        self, provided_interface: ModelInterfaceProvided
    ):
        """Each required field on a frozen model rejects mutation."""
        with pytest.raises(ValidationError):
            provided_interface.id = "new-id"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            provided_interface.kind = EnumInterfaceKind.DATA_MODEL  # type: ignore[misc]

        with pytest.raises(ValidationError):
            provided_interface.surface = EnumInterfaceSurface.SPI  # type: ignore[misc]

        with pytest.raises(ValidationError):
            provided_interface.definition_format = EnumDefinitionFormat.JSON  # type: ignore[misc]

        with pytest.raises(ValidationError):
            provided_interface.definition = "changed"  # type: ignore[misc]

    def test_extra_fields_forbidden(self):
        """extra='forbid' causes ValidationError for unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInterfaceProvided(
                id="iface-extra",
                name="ExtraField",
                kind=EnumInterfaceKind.PROTOCOL,
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
                unknown_field="should fail",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_missing_required_field_raises(self):
        """Missing a required field raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelInterfaceProvided(
                id="iface-missing",
                name="MissingKind",
                # kind is missing
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
            )  # type: ignore[call-arg]

    def test_invalid_kind_enum_rejects(self):
        """Invalid kind value is rejected by Pydantic enum validation."""
        with pytest.raises(ValidationError):
            ModelInterfaceProvided(
                id="iface-bad-kind",
                name="BadKind",
                kind="not_a_valid_kind",  # type: ignore[arg-type]
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
            )

    def test_invalid_surface_enum_rejects(self):
        """Invalid surface value is rejected by Pydantic enum validation."""
        with pytest.raises(ValidationError):
            ModelInterfaceProvided(
                id="iface-bad-surface",
                name="BadSurface",
                kind=EnumInterfaceKind.PROTOCOL,
                surface="not_a_valid_surface",  # type: ignore[arg-type]
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
            )

    def test_invalid_definition_format_enum_rejects(self):
        """Invalid definition_format value is rejected by Pydantic enum validation."""
        with pytest.raises(ValidationError):
            ModelInterfaceProvided(
                id="iface-bad-fmt",
                name="BadFormat",
                kind=EnumInterfaceKind.PROTOCOL,
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format="not_a_valid_format",  # type: ignore[arg-type]
                definition="...",
            )

    def test_invalid_definition_location_rejects(self):
        """definition_location only accepts 'inline' or 'file_ref'."""
        with pytest.raises(ValidationError):
            ModelInterfaceProvided(
                id="iface-bad-loc",
                name="BadLocation",
                kind=EnumInterfaceKind.PROTOCOL,
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
                definition_location="cloud",  # type: ignore[arg-type]
            )

    def test_definition_location_accepts_file_ref(self):
        """definition_location accepts FILE_REF as a valid value."""
        iface = ModelInterfaceProvided(
            id="iface-ref",
            name="FileRef",
            kind=EnumInterfaceKind.PROTOCOL,
            surface=EnumInterfaceSurface.PUBLIC_API,
            definition_format=EnumDefinitionFormat.PYTHON,
            definition="...",
            definition_location=EnumDefinitionLocation.FILE_REF,
            definition_ref="src/protocols/entry.py:ProtocolEntryPoint",
        )
        assert iface.definition_location == EnumDefinitionLocation.FILE_REF
        assert iface.definition_ref == "src/protocols/entry.py:ProtocolEntryPoint"

    def test_all_interface_kinds_accepted(self):
        """Every EnumInterfaceKind value is accepted in construction."""
        for kind in EnumInterfaceKind:
            iface = ModelInterfaceProvided(
                id=f"iface-{kind.value}",
                name=f"Interface_{kind.value}",
                kind=kind,
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
            )
            assert iface.kind == kind

    def test_all_surfaces_accepted(self):
        """Every EnumInterfaceSurface value is accepted in construction."""
        for surface in EnumInterfaceSurface:
            iface = ModelInterfaceProvided(
                id=f"iface-{surface.value}",
                name=f"Interface_{surface.value}",
                kind=EnumInterfaceKind.PROTOCOL,
                surface=surface,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
            )
            assert iface.surface == surface

    def test_all_definition_formats_accepted(self):
        """Every EnumDefinitionFormat value is accepted in construction."""
        for fmt in EnumDefinitionFormat:
            iface = ModelInterfaceProvided(
                id=f"iface-{fmt.value}",
                name=f"Interface_{fmt.value}",
                kind=EnumInterfaceKind.PROTOCOL,
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=fmt,
                definition="...",
            )
            assert iface.definition_format == fmt

    def test_file_ref_without_definition_ref_raises(self):
        """definition_location=FILE_REF with definition_ref=None raises ValidationError."""
        with pytest.raises(ValidationError, match="definition_ref is required"):
            ModelInterfaceProvided(
                id="iface-bad-ref",
                name="MissingRef",
                kind=EnumInterfaceKind.PROTOCOL,
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
                definition_location=EnumDefinitionLocation.FILE_REF,
                definition_ref=None,
            )

    def test_file_ref_without_definition_ref_default_raises(self):
        """definition_location=FILE_REF without explicit definition_ref raises ValidationError."""
        with pytest.raises(ValidationError, match="definition_ref is required"):
            ModelInterfaceProvided(
                id="iface-bad-ref-default",
                name="MissingRefDefault",
                kind=EnumInterfaceKind.PROTOCOL,
                surface=EnumInterfaceSurface.PUBLIC_API,
                definition_format=EnumDefinitionFormat.PYTHON,
                definition="...",
                definition_location=EnumDefinitionLocation.FILE_REF,
            )

    def test_inline_without_definition_ref_is_valid(self):
        """definition_location=INLINE with definition_ref=None is valid."""
        iface = ModelInterfaceProvided(
            id="iface-inline-no-ref",
            name="InlineNoRef",
            kind=EnumInterfaceKind.PROTOCOL,
            surface=EnumInterfaceSurface.PUBLIC_API,
            definition_format=EnumDefinitionFormat.PYTHON,
            definition="...",
            definition_location=EnumDefinitionLocation.INLINE,
            definition_ref=None,
        )
        assert iface.definition_location == EnumDefinitionLocation.INLINE
        assert iface.definition_ref is None

    def test_all_definition_locations_accepted(self):
        """Every EnumDefinitionLocation value is accepted when constraints are met."""
        for loc in EnumDefinitionLocation:
            kwargs: dict[str, object] = {
                "id": f"iface-{loc.value}",
                "name": f"Interface_{loc.value}",
                "kind": EnumInterfaceKind.PROTOCOL,
                "surface": EnumInterfaceSurface.PUBLIC_API,
                "definition_format": EnumDefinitionFormat.PYTHON,
                "definition": "...",
                "definition_location": loc,
            }
            if loc == EnumDefinitionLocation.FILE_REF:
                kwargs["definition_ref"] = "src/foo.py:Bar"
            iface = ModelInterfaceProvided(**kwargs)  # type: ignore[arg-type]
            assert iface.definition_location == loc


# =============================================================================
# E5: EnumDefinitionLocation Tests
# =============================================================================


@pytest.mark.unit
class TestEnumDefinitionLocation:
    """Test EnumDefinitionLocation enum values and behavior."""

    def test_has_all_two_values(self):
        """EnumDefinitionLocation has exactly 2 members."""
        assert len(EnumDefinitionLocation) == 2

    def test_expected_values(self):
        """Each member has the expected string value."""
        assert EnumDefinitionLocation.INLINE.value == "inline"
        assert EnumDefinitionLocation.FILE_REF.value == "file_ref"

    def test_str_returns_value(self):
        """str() on each member returns its string value."""
        for member in EnumDefinitionLocation:
            assert str(member) == member.value

    def test_is_str_subclass(self):
        """EnumDefinitionLocation members are str instances for JSON serialization."""
        for member in EnumDefinitionLocation:
            assert isinstance(member, str)

    def test_values_are_unique(self):
        """All values are unique (enforced by @unique decorator)."""
        values = [m.value for m in EnumDefinitionLocation]
        assert len(values) == len(set(values))


# =============================================================================
# M2: ModelInterfaceConsumed Tests
# =============================================================================


@pytest.mark.unit
class TestModelInterfaceConsumed:
    """Test ModelInterfaceConsumed construction, immutability, and validation."""

    def test_construction_with_required_fields(
        self, consumed_interface: ModelInterfaceConsumed
    ):
        """ModelInterfaceConsumed can be constructed with required fields only."""
        assert consumed_interface.id == "consume-001"
        assert consumed_interface.name == "ProtocolEventBus"
        assert consumed_interface.kind == EnumInterfaceKind.PROTOCOL
        assert consumed_interface.mock_strategy == EnumMockStrategy.PROTOCOL_STUB

    def test_construction_with_all_fields(
        self, full_consumed_interface: ModelInterfaceConsumed
    ):
        """ModelInterfaceConsumed can be constructed with all fields populated."""
        iface = full_consumed_interface
        assert iface.id == "consume-full"
        assert iface.name == "ProtocolLogger"
        assert iface.kind == EnumInterfaceKind.PROTOCOL
        assert iface.source_ticket == "OMN-1937"
        assert iface.mock_strategy == EnumMockStrategy.IN_MEMORY
        assert iface.required is False

    def test_required_defaults_to_true(
        self, consumed_interface: ModelInterfaceConsumed
    ):
        """required field defaults to True."""
        assert consumed_interface.required is True

    def test_source_ticket_is_optional(
        self, consumed_interface: ModelInterfaceConsumed
    ):
        """source_ticket defaults to None when not specified."""
        assert consumed_interface.source_ticket is None

    def test_frozen_immutability(self, consumed_interface: ModelInterfaceConsumed):
        """Frozen model raises ValidationError when mutating a field."""
        with pytest.raises(ValidationError):
            consumed_interface.name = "Modified"  # type: ignore[misc]

    def test_frozen_immutability_all_fields(
        self, consumed_interface: ModelInterfaceConsumed
    ):
        """Each field on a frozen model rejects mutation."""
        with pytest.raises(ValidationError):
            consumed_interface.id = "new-id"  # type: ignore[misc]

        with pytest.raises(ValidationError):
            consumed_interface.kind = EnumInterfaceKind.DATA_MODEL  # type: ignore[misc]

        with pytest.raises(ValidationError):
            consumed_interface.mock_strategy = EnumMockStrategy.NONE  # type: ignore[misc]

        with pytest.raises(ValidationError):
            consumed_interface.required = False  # type: ignore[misc]

    def test_extra_fields_forbidden(self):
        """extra='forbid' causes ValidationError for unknown fields."""
        with pytest.raises(ValidationError) as exc_info:
            ModelInterfaceConsumed(
                id="consume-extra",
                name="ExtraField",
                kind=EnumInterfaceKind.PROTOCOL,
                mock_strategy=EnumMockStrategy.NONE,
                unknown_field="should fail",  # type: ignore[call-arg]
            )

        assert "extra" in str(exc_info.value).lower()

    def test_missing_required_field_raises(self):
        """Missing a required field raises ValidationError."""
        with pytest.raises(ValidationError):
            ModelInterfaceConsumed(
                id="consume-missing",
                name="MissingMock",
                kind=EnumInterfaceKind.PROTOCOL,
                # mock_strategy is missing
            )  # type: ignore[call-arg]

    def test_invalid_kind_enum_rejects(self):
        """Invalid kind value is rejected by Pydantic enum validation."""
        with pytest.raises(ValidationError):
            ModelInterfaceConsumed(
                id="consume-bad-kind",
                name="BadKind",
                kind="not_a_valid_kind",  # type: ignore[arg-type]
                mock_strategy=EnumMockStrategy.NONE,
            )

    def test_invalid_mock_strategy_enum_rejects(self):
        """Invalid mock_strategy value is rejected by Pydantic enum validation."""
        with pytest.raises(ValidationError):
            ModelInterfaceConsumed(
                id="consume-bad-mock",
                name="BadMock",
                kind=EnumInterfaceKind.PROTOCOL,
                mock_strategy="not_a_strategy",  # type: ignore[arg-type]
            )

    def test_all_mock_strategies_accepted(self):
        """Every EnumMockStrategy value is accepted in construction."""
        for strategy in EnumMockStrategy:
            iface = ModelInterfaceConsumed(
                id=f"consume-{strategy.value}",
                name=f"Interface_{strategy.value}",
                kind=EnumInterfaceKind.PROTOCOL,
                mock_strategy=strategy,
            )
            assert iface.mock_strategy == strategy

    def test_all_interface_kinds_accepted(self):
        """Every EnumInterfaceKind value is accepted in construction."""
        for kind in EnumInterfaceKind:
            iface = ModelInterfaceConsumed(
                id=f"consume-{kind.value}",
                name=f"Interface_{kind.value}",
                kind=kind,
                mock_strategy=EnumMockStrategy.NONE,
            )
            assert iface.kind == kind

    def test_required_explicit_false(self):
        """required=False is accepted and persisted correctly."""
        iface = ModelInterfaceConsumed(
            id="consume-opt",
            name="OptionalInterface",
            kind=EnumInterfaceKind.PROTOCOL,
            mock_strategy=EnumMockStrategy.NONE,
            required=False,
        )
        assert iface.required is False

    def test_required_explicit_true(self):
        """required=True is accepted and persisted correctly."""
        iface = ModelInterfaceConsumed(
            id="consume-req",
            name="RequiredInterface",
            kind=EnumInterfaceKind.PROTOCOL,
            mock_strategy=EnumMockStrategy.PROTOCOL_STUB,
            required=True,
        )
        assert iface.required is True


# =============================================================================
# RT: YAML Round-Trip Tests (model_dump / model_validate)
# =============================================================================


@pytest.mark.unit
class TestYAMLRoundTrip:
    """Test round-trip serialization for both interface models."""

    def test_provided_round_trip_minimal(
        self, provided_interface: ModelInterfaceProvided
    ):
        """ModelInterfaceProvided round-trips through model_dump(mode='json') and model_validate."""
        dumped = provided_interface.model_dump(mode="json")
        restored = ModelInterfaceProvided.model_validate(dumped)

        assert restored.id == provided_interface.id
        assert restored.name == provided_interface.name
        assert restored.kind == provided_interface.kind
        assert restored.surface == provided_interface.surface
        assert restored.definition_format == provided_interface.definition_format
        assert restored.definition == provided_interface.definition
        assert restored.definition_hash == provided_interface.definition_hash
        assert restored.definition_location == provided_interface.definition_location
        assert restored.definition_ref == provided_interface.definition_ref
        assert restored.intended_module_path == provided_interface.intended_module_path
        assert restored.version == provided_interface.version

    def test_provided_round_trip_full(
        self, full_provided_interface: ModelInterfaceProvided
    ):
        """Fully-populated ModelInterfaceProvided round-trips correctly."""
        dumped = full_provided_interface.model_dump(mode="json")
        restored = ModelInterfaceProvided.model_validate(dumped)

        assert restored.id == full_provided_interface.id
        assert restored.name == full_provided_interface.name
        assert restored.kind == full_provided_interface.kind
        assert restored.surface == full_provided_interface.surface
        assert restored.definition_format == full_provided_interface.definition_format
        assert restored.definition == full_provided_interface.definition
        assert restored.definition_hash == full_provided_interface.definition_hash
        assert (
            restored.definition_location == full_provided_interface.definition_location
        )
        assert restored.definition_ref == full_provided_interface.definition_ref
        assert (
            restored.intended_module_path
            == full_provided_interface.intended_module_path
        )
        assert restored.version == full_provided_interface.version

    def test_consumed_round_trip_minimal(
        self, consumed_interface: ModelInterfaceConsumed
    ):
        """ModelInterfaceConsumed round-trips through model_dump(mode='json') and model_validate."""
        dumped = consumed_interface.model_dump(mode="json")
        restored = ModelInterfaceConsumed.model_validate(dumped)

        assert restored.id == consumed_interface.id
        assert restored.name == consumed_interface.name
        assert restored.kind == consumed_interface.kind
        assert restored.source_ticket == consumed_interface.source_ticket
        assert restored.mock_strategy == consumed_interface.mock_strategy
        assert restored.required == consumed_interface.required

    def test_consumed_round_trip_full(
        self, full_consumed_interface: ModelInterfaceConsumed
    ):
        """Fully-populated ModelInterfaceConsumed round-trips correctly."""
        dumped = full_consumed_interface.model_dump(mode="json")
        restored = ModelInterfaceConsumed.model_validate(dumped)

        assert restored.id == full_consumed_interface.id
        assert restored.name == full_consumed_interface.name
        assert restored.kind == full_consumed_interface.kind
        assert restored.source_ticket == full_consumed_interface.source_ticket
        assert restored.mock_strategy == full_consumed_interface.mock_strategy
        assert restored.required == full_consumed_interface.required

    def test_provided_enums_serialize_as_strings(
        self, provided_interface: ModelInterfaceProvided
    ):
        """Enum fields serialize to plain strings in JSON mode, not Python object notation."""
        dumped = provided_interface.model_dump(mode="json")

        assert isinstance(dumped["kind"], str)
        assert dumped["kind"] == "protocol"
        assert not dumped["kind"].startswith("EnumInterfaceKind")

        assert isinstance(dumped["surface"], str)
        assert dumped["surface"] == "public_api"
        assert not dumped["surface"].startswith("EnumInterfaceSurface")

        assert isinstance(dumped["definition_format"], str)
        assert dumped["definition_format"] == "python"
        assert not dumped["definition_format"].startswith("EnumDefinitionFormat")

    def test_consumed_enums_serialize_as_strings(
        self, consumed_interface: ModelInterfaceConsumed
    ):
        """Enum fields serialize to plain strings in JSON mode, not Python object notation."""
        dumped = consumed_interface.model_dump(mode="json")

        assert isinstance(dumped["kind"], str)
        assert dumped["kind"] == "protocol"

        assert isinstance(dumped["mock_strategy"], str)
        assert dumped["mock_strategy"] == "protocol_stub"
        assert not dumped["mock_strategy"].startswith("EnumMockStrategy")

    def test_provided_model_dump_is_json_serializable(
        self, full_provided_interface: ModelInterfaceProvided
    ):
        """model_dump(mode='json') output is fully JSON-serializable."""
        import json

        dumped = full_provided_interface.model_dump(mode="json")
        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)

    def test_consumed_model_dump_is_json_serializable(
        self, full_consumed_interface: ModelInterfaceConsumed
    ):
        """model_dump(mode='json') output is fully JSON-serializable."""
        import json

        dumped = full_consumed_interface.model_dump(mode="json")
        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)

    def test_provided_from_attributes_compatibility(self):
        """ModelInterfaceProvided with from_attributes=True accepts attribute-style input."""
        # model_validate with from_attributes allows dict input
        data = {
            "id": "attr-test",
            "name": "AttrTest",
            "kind": "protocol",
            "surface": "public_api",
            "definition_format": "python",
            "definition": "...",
        }
        iface = ModelInterfaceProvided.model_validate(data)
        assert iface.id == "attr-test"
        assert iface.kind == EnumInterfaceKind.PROTOCOL

    def test_consumed_from_attributes_compatibility(self):
        """ModelInterfaceConsumed with from_attributes=True accepts attribute-style input."""
        data = {
            "id": "attr-test",
            "name": "AttrTest",
            "kind": "protocol",
            "mock_strategy": "in_memory",
        }
        iface = ModelInterfaceConsumed.model_validate(data)
        assert iface.id == "attr-test"
        assert iface.mock_strategy == EnumMockStrategy.IN_MEMORY


# =============================================================================
# VERIFY_INTERFACE Enum Tests (OMN-1971)
# =============================================================================


@pytest.mark.unit
class TestVerifyInterfaceEnum:
    """Test VERIFY_INTERFACE enum value in EnumVerificationKind."""

    def test_verify_interface_exists(self):
        """EnumVerificationKind has VERIFY_INTERFACE member."""
        from omnibase_core.enums.ticket.enum_ticket_types import EnumVerificationKind

        assert hasattr(EnumVerificationKind, "VERIFY_INTERFACE")

    def test_verify_interface_value(self):
        """VERIFY_INTERFACE has expected string value."""
        from omnibase_core.enums.ticket.enum_ticket_types import EnumVerificationKind

        assert EnumVerificationKind.VERIFY_INTERFACE.value == "verify_interface"

    def test_verify_interface_is_str(self):
        """VERIFY_INTERFACE is a str instance for JSON serialization."""
        from omnibase_core.enums.ticket.enum_ticket_types import EnumVerificationKind

        assert isinstance(EnumVerificationKind.VERIFY_INTERFACE, str)

    def test_verify_interface_str_returns_value(self):
        """str(VERIFY_INTERFACE) returns the string value."""
        from omnibase_core.enums.ticket.enum_ticket_types import EnumVerificationKind

        assert str(EnumVerificationKind.VERIFY_INTERFACE) == "verify_interface"

    def test_enum_count_includes_verify_interface(self):
        """EnumVerificationKind now has 7 members (was 6)."""
        from omnibase_core.enums.ticket.enum_ticket_types import EnumVerificationKind

        assert len(EnumVerificationKind) == 7


# =============================================================================
# Integration: ModelTicketContract with Interfaces (OMN-1971)
# =============================================================================


@pytest.mark.unit
class TestTicketContractInterfaceIntegration:
    """Test interfaces_provided/consumed fields on ModelTicketContract."""

    def test_contract_default_empty_interfaces(self):
        """New contract has empty interfaces_provided and interfaces_consumed."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-001",
            title="Integration Test",
        )
        assert contract.interfaces_provided == []
        assert contract.interfaces_consumed == []

    def test_contract_with_interfaces_provided(
        self, provided_interface: ModelInterfaceProvided
    ):
        """Contract accepts interfaces_provided list."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-002",
            title="With Provided",
            interfaces_provided=[provided_interface],
        )
        assert len(contract.interfaces_provided) == 1
        assert contract.interfaces_provided[0].id == "iface-001"
        assert contract.interfaces_provided[0].name == "ProtocolRuntimeEntryPoint"

    def test_contract_with_interfaces_consumed(
        self, consumed_interface: ModelInterfaceConsumed
    ):
        """Contract accepts interfaces_consumed list."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-003",
            title="With Consumed",
            interfaces_consumed=[consumed_interface],
        )
        assert len(contract.interfaces_consumed) == 1
        assert contract.interfaces_consumed[0].id == "consume-001"
        assert contract.interfaces_consumed[0].name == "ProtocolEventBus"

    def test_contract_with_both_interfaces(
        self,
        provided_interface: ModelInterfaceProvided,
        consumed_interface: ModelInterfaceConsumed,
    ):
        """Contract accepts both interfaces_provided and interfaces_consumed."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-004",
            title="Both Interfaces",
            interfaces_provided=[provided_interface],
            interfaces_consumed=[consumed_interface],
        )
        assert len(contract.interfaces_provided) == 1
        assert len(contract.interfaces_consumed) == 1

    def test_contract_with_multiple_interfaces(
        self,
        provided_interface: ModelInterfaceProvided,
        full_provided_interface: ModelInterfaceProvided,
        consumed_interface: ModelInterfaceConsumed,
        full_consumed_interface: ModelInterfaceConsumed,
    ):
        """Contract accepts multiple interfaces in each list."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-005",
            title="Multiple Interfaces",
            interfaces_provided=[provided_interface, full_provided_interface],
            interfaces_consumed=[consumed_interface, full_consumed_interface],
        )
        assert len(contract.interfaces_provided) == 2
        assert len(contract.interfaces_consumed) == 2

    def test_contract_yaml_round_trip_with_interfaces(
        self,
        provided_interface: ModelInterfaceProvided,
        consumed_interface: ModelInterfaceConsumed,
    ):
        """Interfaces survive YAML serialization round-trip."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-RT",
            title="YAML Round Trip",
            interfaces_provided=[provided_interface],
            interfaces_consumed=[consumed_interface],
        )

        yaml_str = contract.to_yaml()
        restored = ModelTicketContract.from_yaml(yaml_str)

        assert len(restored.interfaces_provided) == 1
        assert restored.interfaces_provided[0].id == "iface-001"
        assert restored.interfaces_provided[0].name == "ProtocolRuntimeEntryPoint"
        assert restored.interfaces_provided[0].kind == EnumInterfaceKind.PROTOCOL
        assert (
            restored.interfaces_provided[0].surface == EnumInterfaceSurface.PUBLIC_API
        )

        assert len(restored.interfaces_consumed) == 1
        assert restored.interfaces_consumed[0].id == "consume-001"
        assert restored.interfaces_consumed[0].name == "ProtocolEventBus"
        assert restored.interfaces_consumed[0].kind == EnumInterfaceKind.PROTOCOL
        assert (
            restored.interfaces_consumed[0].mock_strategy
            == EnumMockStrategy.PROTOCOL_STUB
        )

    def test_contract_yaml_round_trip_with_full_interfaces(
        self,
        full_provided_interface: ModelInterfaceProvided,
        full_consumed_interface: ModelInterfaceConsumed,
    ):
        """Fully-populated interfaces survive YAML round-trip."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-FULL-RT",
            title="Full YAML Round Trip",
            interfaces_provided=[full_provided_interface],
            interfaces_consumed=[full_consumed_interface],
        )

        yaml_str = contract.to_yaml()
        restored = ModelTicketContract.from_yaml(yaml_str)

        rp = restored.interfaces_provided[0]
        assert rp.definition_hash == "abc123def456"
        assert rp.definition_location == EnumDefinitionLocation.FILE_REF
        assert rp.definition_ref == "src/models/events.py:ModelUserEvent"
        assert rp.intended_module_path == "omnibase_core.models.events"
        assert rp.version == "1.2.0"

        rc = restored.interfaces_consumed[0]
        assert rc.source_ticket == "OMN-1937"
        assert rc.mock_strategy == EnumMockStrategy.IN_MEMORY
        assert rc.required is False

    def test_contract_model_dump_includes_interfaces(
        self,
        provided_interface: ModelInterfaceProvided,
        consumed_interface: ModelInterfaceConsumed,
    ):
        """model_dump(mode='json') includes interface fields."""
        import json

        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-DUMP",
            title="Dump Test",
            interfaces_provided=[provided_interface],
            interfaces_consumed=[consumed_interface],
        )

        dumped = contract.model_dump(mode="json")

        assert "interfaces_provided" in dumped
        assert "interfaces_consumed" in dumped
        assert len(dumped["interfaces_provided"]) == 1
        assert len(dumped["interfaces_consumed"]) == 1

        # Verify JSON serializable
        json_str = json.dumps(dumped)
        assert isinstance(json_str, str)

    def test_contract_interfaces_in_yaml_output(
        self,
        provided_interface: ModelInterfaceProvided,
    ):
        """Interface data appears in YAML output as plain strings."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-INT-YAML",
            title="YAML Output",
            interfaces_provided=[provided_interface],
        )

        yaml_str = contract.to_yaml()

        assert "interfaces_provided" in yaml_str
        assert "ProtocolRuntimeEntryPoint" in yaml_str
        assert "!!python" not in yaml_str


# =============================================================================
# Backward Compatibility Tests (OMN-1971)
# =============================================================================


@pytest.mark.unit
class TestBackwardCompatibility:
    """Existing contracts without interface fields still load correctly."""

    def test_old_contract_without_interfaces_loads(self):
        """YAML contract missing interfaces fields loads with empty defaults."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        old_yaml = """
ticket_id: OMN-OLD
title: Legacy Contract
phase: intake
description: ""
context: {}
questions: []
requirements: []
verification_steps: []
gates: []
"""
        contract = ModelTicketContract.from_yaml(old_yaml)
        assert contract.ticket_id == "OMN-OLD"
        assert contract.interfaces_provided == []
        assert contract.interfaces_consumed == []

    def test_old_contract_dict_without_interfaces_validates(self):
        """Dict input missing interfaces fields validates with defaults."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        data = {
            "ticket_id": "OMN-OLD-DICT",
            "title": "Legacy Dict Contract",
        }
        contract = ModelTicketContract.model_validate(data)
        assert contract.interfaces_provided == []
        assert contract.interfaces_consumed == []

    def test_old_contract_round_trip_preserves_empty_interfaces(self):
        """Contract created without interfaces round-trips with empty lists."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-OLD-RT",
            title="Legacy Round Trip",
        )
        yaml_str = contract.to_yaml()
        restored = ModelTicketContract.from_yaml(yaml_str)

        assert restored.interfaces_provided == []
        assert restored.interfaces_consumed == []


# =============================================================================
# Fingerprint Stability Tests (OMN-1971)
# =============================================================================


@pytest.mark.unit
class TestFingerprintStability:
    """Hash input is normalized — same content = same hash."""

    def test_fingerprint_changes_with_interfaces(
        self,
        provided_interface: ModelInterfaceProvided,
    ):
        """Adding interfaces changes the fingerprint."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-FP-001",
            title="Fingerprint Test",
        )
        fp_without = contract.compute_fingerprint()

        contract.interfaces_provided = [provided_interface]
        fp_with = contract.compute_fingerprint()

        assert fp_without != fp_with

    def test_fingerprint_deterministic_with_interfaces(
        self,
        provided_interface: ModelInterfaceProvided,
        consumed_interface: ModelInterfaceConsumed,
    ):
        """Same interfaces produce the same fingerprint."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-FP-002",
            title="Deterministic FP",
            interfaces_provided=[provided_interface],
            interfaces_consumed=[consumed_interface],
        )
        fp1 = contract.compute_fingerprint()
        fp2 = contract.compute_fingerprint()

        assert fp1 == fp2

    def test_fingerprint_stable_after_yaml_round_trip(
        self,
        provided_interface: ModelInterfaceProvided,
        consumed_interface: ModelInterfaceConsumed,
    ):
        """Fingerprint is identical before and after YAML round-trip."""
        from omnibase_core.models.ticket.model_ticket_contract import (
            ModelTicketContract,
        )

        contract = ModelTicketContract(
            ticket_id="OMN-FP-003",
            title="Stable FP",
            interfaces_provided=[provided_interface],
            interfaces_consumed=[consumed_interface],
        )
        fp_before = contract.compute_fingerprint()

        yaml_str = contract.to_yaml()
        restored = ModelTicketContract.from_yaml(yaml_str)
        fp_after = restored.compute_fingerprint()

        assert fp_before == fp_after


# =============================================================================
# definition_hash Tests (OMN-1971)
# =============================================================================


@pytest.mark.unit
class TestDefinitionHash:
    """definition_hash matches SHA256 of normalized definition content."""

    def test_definition_hash_matches_sha256(self):
        """definition_hash can be verified against SHA256 of definition."""
        import hashlib

        definition = "class ProtocolRuntimeEntryPoint(Protocol): ..."
        expected_hash = hashlib.sha256(definition.encode()).hexdigest()

        iface = ModelInterfaceProvided(
            id="hash-test",
            name="HashTest",
            kind=EnumInterfaceKind.PROTOCOL,
            surface=EnumInterfaceSurface.PUBLIC_API,
            definition_format=EnumDefinitionFormat.PYTHON,
            definition=definition,
            definition_hash=expected_hash,
        )
        assert iface.definition_hash == expected_hash

    def test_definition_hash_is_optional(self):
        """definition_hash is optional and defaults to None."""
        iface = ModelInterfaceProvided(
            id="no-hash",
            name="NoHash",
            kind=EnumInterfaceKind.PROTOCOL,
            surface=EnumInterfaceSurface.PUBLIC_API,
            definition_format=EnumDefinitionFormat.PYTHON,
            definition="...",
        )
        assert iface.definition_hash is None

    def test_definition_hash_survives_round_trip(self):
        """definition_hash is preserved through model_dump / model_validate."""
        import hashlib

        definition = "type: object\nproperties:\n  user_id: {type: string}"
        expected_hash = hashlib.sha256(definition.encode()).hexdigest()

        iface = ModelInterfaceProvided(
            id="hash-rt",
            name="HashRT",
            kind=EnumInterfaceKind.PROTOCOL,
            surface=EnumInterfaceSurface.PUBLIC_API,
            definition_format=EnumDefinitionFormat.YAML,
            definition=definition,
            definition_hash=expected_hash,
        )

        dumped = iface.model_dump(mode="json")
        restored = ModelInterfaceProvided.model_validate(dumped)

        assert restored.definition_hash == expected_hash

    def test_definition_hash_formatting_independent(self):
        """Same logical content produces the same hash regardless of whitespace."""
        import hashlib

        # Normalize by stripping and collapsing whitespace
        def normalize(s: str) -> str:
            return " ".join(s.split())

        definition_v1 = "class   Foo(Protocol):   pass"
        definition_v2 = "class Foo(Protocol): pass"

        hash_v1 = hashlib.sha256(normalize(definition_v1).encode()).hexdigest()
        hash_v2 = hashlib.sha256(normalize(definition_v2).encode()).hexdigest()

        assert hash_v1 == hash_v2
