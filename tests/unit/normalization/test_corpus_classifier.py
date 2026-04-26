# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for corpus_classifier.classify_contract_path (OMN-9760, parent OMN-9757).

Validates path-based bucket assignment with secondary shape signals per the
corpus-classification-and-normalization plan:

* path classification is primary (never overridden by shape)
* ``reasons`` is always non-empty
* ``confidence`` is None for certain classifications, < 0.5 for unknown-path
  fallback, 0.7 when path matches but raw shape is missing expected fields
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.enums.enum_contract_bucket import EnumContractBucket
from omnibase_core.models.contracts.model_corpus_classification import (
    ModelCorpusClassification,
)
from omnibase_core.normalization.corpus_classifier import classify_contract_path


@pytest.mark.unit
class TestBucketAssignment:
    """Path globs map to the correct bucket."""

    def test_node_root_contract_bucket(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT
        assert len(result.reasons) > 0

    def test_handler_contract_bucket(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo/handlers/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.bucket is EnumContractBucket.HANDLER_CONTRACT
        assert len(result.reasons) > 0

    def test_integration_contract_bucket(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/integrations/github_webhook/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.bucket is EnumContractBucket.INTEGRATION_CONTRACT
        assert len(result.reasons) > 0

    def test_package_contract_not_under_nodes(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/contracts/verification/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.bucket is EnumContractBucket.PACKAGE_CONTRACT
        assert len(result.reasons) > 0


@pytest.mark.unit
class TestRequiresValidation:
    """``requires_validation`` is True only for node_root_contract."""

    def test_node_root_returns_requires_validation_true(self) -> None:
        path = Path("omniclaude/src/omniclaude/nodes/node_bar_compute/contract.yaml")
        result = classify_contract_path(path)
        assert result.requires_validation is True
        assert len(result.reasons) > 0

    def test_non_node_bucket_skips_validation(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/integrations/github_webhook/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.requires_validation is False
        assert len(result.reasons) > 0

    def test_handler_contract_skips_validation(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo/handlers/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.requires_validation is False


@pytest.mark.unit
class TestRawNodeTypeExtraction:
    """``raw_node_type`` is populated when a raw dict is provided."""

    def test_node_type_extracted_from_raw(self) -> None:
        raw = {"node_type": "EFFECT", "name": "node_foo_effect"}
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path, raw=raw)
        assert result.raw_node_type == "EFFECT"

    def test_no_raw_dict_yields_none_node_type(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.raw_node_type is None

    def test_non_string_node_type_returns_none(self) -> None:
        raw: dict[str, object] = {"node_type": 42, "name": "node_x"}
        path = Path("omnibase_infra/src/omnibase_infra/nodes/node_x/contract.yaml")
        result = classify_contract_path(path, raw=raw)
        assert result.raw_node_type is None


@pytest.mark.unit
class TestConfidenceAndReasons:
    """Confidence + reasons signal classification quality."""

    def test_confidence_none_for_certain_classification(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.confidence is None

    def test_confidence_set_for_unknown_path(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo/oddly/nested/contract.yaml"
        )
        result = classify_contract_path(path)
        assert result.bucket is EnumContractBucket.UNKNOWN
        assert result.confidence is not None
        assert result.confidence < 0.5

    def test_shape_signal_adds_reason(self) -> None:
        raw = {"node_type": "EFFECT_GENERIC", "name": "node_foo_effect"}
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path, raw=raw)
        assert any("node_type" in r for r in result.reasons)

    def test_path_match_shape_mismatch_lowers_confidence(self) -> None:
        raw = {"name": "node_foo_effect"}  # node_type missing
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path, raw=raw)
        assert result.bucket is EnumContractBucket.NODE_ROOT_CONTRACT
        assert result.confidence == 0.7

    def test_handler_class_block_adds_reason(self) -> None:
        raw = {"handler": {"class": "HandlerFoo"}}
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo/handlers/contract.yaml"
        )
        result = classify_contract_path(path, raw=raw)
        assert any("handler.class" in r for r in result.reasons)


@pytest.mark.unit
class TestModelCorpusClassificationStructure:
    """The returned model is the canonical Pydantic v2 type."""

    def test_returns_model_corpus_classification(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path)
        assert isinstance(result, ModelCorpusClassification)

    def test_model_is_frozen(self) -> None:
        path = Path(
            "omnibase_infra/src/omnibase_infra/nodes/node_foo_effect/contract.yaml"
        )
        result = classify_contract_path(path)
        with pytest.raises(Exception):
            result.bucket = EnumContractBucket.UNKNOWN  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ModelCorpusClassification(
                path=Path("a/b/contract.yaml"),
                bucket=EnumContractBucket.UNKNOWN,
                requires_validation=False,
                bogus_field="x",  # type: ignore[call-arg]
            )
