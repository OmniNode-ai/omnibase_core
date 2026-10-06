# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Oracle parity with permanent non-vacuous synthetic goldens."""

import json
from pathlib import Path

import pytest

from omnibase_core.models.nodes.exposed_identifiers_check.model_exposed_identifiers_check_input import (
    ModelExposedIdentifiersCheckInput,
)
from omnibase_core.models.nodes.no_utcnow_check.model_source_file import ModelSourceFile
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.handler import (
    NodeExposedIdentifiersCheckCompute,
)
from omnibase_core.nodes.node_exposed_identifiers_check_compute.runtime_exposed_identifiers_check import (
    main,
)

from .parity_support import FIXTURES, SYNTHETIC, corpus, denylist_text

pytestmark = pytest.mark.unit


def findings(files: dict[str, str]) -> list[str]:
    report = NodeExposedIdentifiersCheckCompute().handle(
        ModelExposedIdentifiersCheckInput(
            files=[
                ModelSourceFile(path=path, source=source)
                for path, source in files.items()
            ],
            denylist_json=denylist_text(),
        )
    )
    return [f"{hit.location}: {hit.message}" for hit in report.findings]


def test_parity_golden() -> None:
    files = corpus()
    golden = json.loads((FIXTURES / "golden.json").read_text())
    actual = findings(files)
    assert actual == golden["findings"]
    assert len(actual) == 7
    assert all(SYNTHETIC not in finding for finding in actual)


def test_parity_removing_expected_hit_fails_comparison() -> None:
    files = corpus()
    files["bare.txt"] = "clean content\n"
    golden = json.loads((FIXTURES / "golden.json").read_text())
    with pytest.raises(AssertionError):
        assert findings(files) == golden["findings"]


def test_runtime_corpus_verdict_and_report_match_golden(tmp_path: Path) -> None:
    root = tmp_path / "root"
    paths = []
    for path, source in corpus().items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.encode())
        paths.append(str(target))
    denylist = tmp_path / "denylist.json"
    denylist.write_text(denylist_text())
    output = tmp_path / "report.json"
    golden = json.loads((FIXTURES / "golden.json").read_text())
    assert (
        main(
            [
                "--root",
                str(root),
                "--denylist",
                str(denylist),
                "--report-json",
                str(output),
                *paths,
            ]
        )
        == golden["exit_code"]
    )
    report = ModelValidationReport.model_validate_json(output.read_text())
    assert [f"{hit.location}: {hit.message}" for hit in report.findings] == golden[
        "findings"
    ]


@pytest.mark.parametrize(
    "document",
    ["{", "[]", "{}", '{"salt":"x","entries":[]}', '{"salt":"x","entries":[null]}'],
)
def test_malformed_denylist_is_error(document: str) -> None:
    report = NodeExposedIdentifiersCheckCompute().handle(
        ModelExposedIdentifiersCheckInput(denylist_json=document)
    )
    assert report.overall_status == "ERROR"


@pytest.mark.parametrize(
    "change",
    [
        {"length": 3},
        {"length": "4"},
        {"sha256": "BAD"},
        {"value": SYNTHETIC},
        {"literal": SYNTHETIC},
        {"plaintext": SYNTHETIC},
    ],
)
def test_denylist_entry_errors(change: dict[str, object]) -> None:
    doc = json.loads(denylist_text())
    doc["entries"][0].update(change)
    report = NodeExposedIdentifiersCheckCompute().handle(
        ModelExposedIdentifiersCheckInput(denylist_json=json.dumps(doc))
    )
    assert report.overall_status == "ERROR"
    assert SYNTHETIC not in report.model_dump_json()


@pytest.mark.parametrize("field", ["id", "kind", "length", "sha256", "ticket"])
def test_required_entry_fields(field: str) -> None:
    doc = json.loads(denylist_text())
    del doc["entries"][0][field]
    report = NodeExposedIdentifiersCheckCompute().handle(
        ModelExposedIdentifiersCheckInput(denylist_json=json.dumps(doc))
    )
    assert report.overall_status == "ERROR"
    assert f"missing '{field}'" in report.findings[0].message


@pytest.mark.parametrize(
    ("annotation", "count"),
    json.loads((FIXTURES / "annotation_cases.json").read_text()),
)
def test_annotation_discipline(annotation: str, count: int) -> None:
    assert len(findings({"sample.txt": f"{SYNTHETIC} {annotation}\n"})) == count
    # A valid waiver only covers its own line.
    assert len(findings({"sample.txt": f"{annotation}\n{SYNTHETIC}\n"})) == 1


def test_disjoint_hits_both_survive_overlap_collapse() -> None:
    hits = findings({"sample.txt": f"{SYNTHETIC} / {SYNTHETIC}\n"})
    assert len(hits) == 2
    assert all("entry=synthetic-0" in hit for hit in hits)
    assert hits[0].startswith("sample.txt:1:1:")
    assert hits[1].startswith(f"sample.txt:1:{len(SYNTHETIC) + 4}:")


@pytest.mark.parametrize(
    ("extra", "count"), [(512 - len(SYNTHETIC), 1), (513 - len(SYNTHETIC), 0)]
)
def test_token_size_boundary(extra: int, count: int) -> None:
    assert len(findings({"sample.txt": SYNTHETIC + "x" * extra})) == count
