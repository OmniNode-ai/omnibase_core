# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Import-order regressions for mixin-mapping canonical owners (OMN-17709)."""

from __future__ import annotations

import copy
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from omnibase_core.models.core.model_mixin_mapping import ModelMixinMapping
from omnibase_core.models.core.model_mixin_mapping_collection import (
    ModelMixinMappingCollection,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parents[4]


def _mapping_payload() -> dict[str, object]:
    return {
        "mixin_name": "MixinMetrics",
        "handler_contract_stub": "contracts/handlers/metrics_handler.yaml",
        "handler_type_category": "compute",
        "capability_set": ["metrics", "observability"],
        "nondeterminism_classification": "deterministic",
        "legacy_shim_required": False,
        "conversion_evidence": "test:test_metrics_pure",
    }


def _run_fresh_python(source: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        cwd=_REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "first_import",
    [
        "import omnibase_core.models.core.model_mixin_mapping as mapping_module",
        "import omnibase_core.models.core.model_mixin_mapping_collection as collection_module",
    ],
)
def test_models_are_complete_before_instances_in_both_fresh_import_orders(
    first_import: str,
) -> None:
    result = _run_fresh_python(
        f"""
        {first_import}
        import omnibase_core.models.core.model_mixin_mapping as mapping_module
        from omnibase_core.models.core.model_mixin_mapping import ModelMixinMapping
        from omnibase_core.models.core.model_mixin_mapping_collection import ModelMixinMappingCollection

        assert not hasattr(mapping_module, "ModelMixinMappingCollection")
        assert ModelMixinMapping.__pydantic_complete__ is True
        assert ModelMixinMappingCollection.__pydantic_complete__ is True
        assert ModelMixinMapping.model_json_schema()["title"] == "ModelMixinMapping"
        assert ModelMixinMappingCollection.model_json_schema()["title"] == "ModelMixinMappingCollection"
        """
    )

    assert result.returncode == 0, result.stderr


def test_collection_mapping_and_json_round_trip_preserve_leaf_type() -> None:
    collection = ModelMixinMappingCollection.model_validate(
        {"mixins": [_mapping_payload()]}
    )
    restored = ModelMixinMappingCollection.model_validate_json(
        collection.model_dump_json()
    )

    assert restored == collection
    assert isinstance(restored.mixins[0], ModelMixinMapping)


@pytest.mark.parametrize("unknown_location", ["collection", "mapping"])
def test_collection_rejects_unknown_fields_at_both_contract_boundaries(
    unknown_location: str,
) -> None:
    payload: dict[str, object] = {"mixins": [_mapping_payload()]}
    if unknown_location == "collection":
        payload["omn17709_unknown"] = True
    else:
        mapping_payload = cast(
            dict[str, object],
            cast(list[object], payload["mixins"])[0],
        )
        mapping_payload["omn17709_unknown"] = True

    with pytest.raises(ValidationError) as exc_info:
        ModelMixinMappingCollection.model_validate(copy.deepcopy(payload))

    assert any(error["type"] == "extra_forbidden" for error in exc_info.value.errors())
