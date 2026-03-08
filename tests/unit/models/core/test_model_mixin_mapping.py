# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for ModelMixinMapping and ModelMixinMappingCollection (OMN-1115)."""

import pytest

from omnibase_core.enums.enum_handler_type_category import EnumHandlerTypeCategory
from omnibase_core.enums.enum_nondeterminism_class import EnumNondeterminismClass
from omnibase_core.models.core.model_mixin_mapping import (
    ModelMixinMapping,
    ModelMixinMappingCollection,
)


@pytest.mark.unit
class TestModelMixinMapping:
    """Tests for the mixin mapping model."""

    def test_create_compute_mapping(self) -> None:
        """Create a deterministic compute mapping."""
        mapping = ModelMixinMapping(
            mixin_name="MixinMetrics",
            handler_contract_stub="contracts/handlers/metrics_handler.yaml",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            capability_set=["metrics", "observability"],
            nondeterminism_classification=EnumNondeterminismClass.DETERMINISTIC,
            legacy_shim_required=False,
            conversion_evidence="test:test_metrics_pure",
        )
        assert mapping.mixin_name == "MixinMetrics"
        assert mapping.handler_type_category == EnumHandlerTypeCategory.COMPUTE
        assert (
            mapping.nondeterminism_classification
            == EnumNondeterminismClass.DETERMINISTIC
        )
        assert mapping.legacy_shim_required is False
        assert mapping.conversion_evidence == "test:test_metrics_pure"

    def test_create_effect_mapping(self) -> None:
        """Create a network effect mapping."""
        mapping = ModelMixinMapping(
            mixin_name="MixinEventBus",
            handler_contract_stub="contracts/handlers/event_bus_handler.yaml",
            handler_type_category=EnumHandlerTypeCategory.EFFECT,
            capability_set=["event_publishing", "event_subscription"],
            nondeterminism_classification=EnumNondeterminismClass.NETWORK,
        )
        assert mapping.handler_type_category == EnumHandlerTypeCategory.EFFECT
        assert mapping.nondeterminism_classification == EnumNondeterminismClass.NETWORK
        assert mapping.legacy_shim_required is True
        assert mapping.conversion_evidence is None

    def test_default_legacy_shim(self) -> None:
        """legacy_shim_required defaults to True."""
        mapping = ModelMixinMapping(
            mixin_name="MixinTest",
            handler_contract_stub="stub.yaml",
            handler_type_category=EnumHandlerTypeCategory.COMPUTE,
            nondeterminism_classification=EnumNondeterminismClass.DETERMINISTIC,
        )
        assert mapping.legacy_shim_required is True

    def test_serialization_roundtrip(self) -> None:
        """Model serializes and deserializes correctly."""
        mapping = ModelMixinMapping(
            mixin_name="MixinCaching",
            handler_contract_stub="contracts/handlers/caching_handler.yaml",
            handler_type_category=EnumHandlerTypeCategory.NONDETERMINISTIC_COMPUTE,
            capability_set=["caching", "performance"],
            nondeterminism_classification=EnumNondeterminismClass.TIME,
        )
        data = mapping.model_dump()
        restored = ModelMixinMapping.model_validate(data)
        assert restored == mapping


@pytest.mark.unit
class TestModelMixinMappingCollection:
    """Tests for the mixin mapping collection model."""

    def test_empty_collection(self) -> None:
        """Empty collection creates successfully."""
        collection = ModelMixinMappingCollection()
        assert len(collection.mixins) == 0

    def test_collection_with_mappings(self) -> None:
        """Collection holds multiple mappings."""
        mappings = [
            ModelMixinMapping(
                mixin_name="MixinA",
                handler_contract_stub="a.yaml",
                handler_type_category=EnumHandlerTypeCategory.COMPUTE,
                nondeterminism_classification=EnumNondeterminismClass.DETERMINISTIC,
            ),
            ModelMixinMapping(
                mixin_name="MixinB",
                handler_contract_stub="b.yaml",
                handler_type_category=EnumHandlerTypeCategory.EFFECT,
                nondeterminism_classification=EnumNondeterminismClass.NETWORK,
            ),
        ]
        collection = ModelMixinMappingCollection(mixins=mappings)
        assert len(collection.mixins) == 2
        assert collection.mixins[0].mixin_name == "MixinA"
        assert collection.mixins[1].mixin_name == "MixinB"
