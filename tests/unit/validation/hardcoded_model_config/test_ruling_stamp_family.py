# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Policy-driven hardcoded value fixtures for OMN-21503."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from omnibase_core.validation.hardcoded_model_config.handler import (
    added_entries,
    compare_with_baseline,
    scan,
)
from omnibase_core.validation.hardcoded_model_config.models import (
    ModelHardcodedModelConfigBaselineEntry,
    ModelHardcodedModelConfigPolicy,
)
from omnibase_core.validation.hardcoded_model_config.runtime_hardcoded_model_config import (
    load_policy,
)

pytestmark = pytest.mark.unit
STAMP = "2026-10-28T12:34:56.123Z"


@pytest.mark.parametrize(
    "value", [f"RULING {STAMP}", f"{STAMP} ruling", f"ruling{' ' * 120}{STAMP}"]
)
@pytest.mark.parametrize("path", ["src/app.py", "src/settings.yaml"])
def test_source_refuses_stamp(value: str, path: str) -> None:
    findings = scan(
        path,
        f'VALUE = "{value}"\n' if path.endswith(".py") else f'value: "{value}"\n',
        load_policy(),
    )
    assert [f.family for f in findings] == ["S"]


@pytest.mark.parametrize(
    "text",
    [
        f"# ruling {STAMP}\n",
        f'"""ruling {STAMP}"""\n',
        f'VALUE = "ordinary"  # ruling {STAMP}\n',
        f'VALUE = "ruling{" " * 121}{STAMP}"\n',
        f'VALUE = "overruling {STAMP}"\n',
        f'VALUE = """ruling\n{STAMP}"""\n',
    ],
)
def test_comments_docstrings_and_nonmatches(text: str) -> None:
    assert scan("src/app.py", text, load_policy()) == []


@pytest.mark.parametrize(
    "path", ["tests/sample.py", "config/onex/overlays/sample.yaml", "docs/sample.md"]
)
def test_other_classes_allow_stamp(path: str) -> None:
    assert scan(path, f'VALUE = "ruling {STAMP}"\n', load_policy()) == []


def test_stamp_baseline_is_a_path_family_content_multiset() -> None:
    text = f'VALUE = "ruling {STAMP}"\n'
    findings = scan("src/app.py", text * 2, load_policy())
    assert len(findings) == 2
    entry = ModelHardcodedModelConfigBaselineEntry(
        path="src/app.py", family="S", content_sha1=findings[0].content_sha1
    )
    new, stale = compare_with_baseline(
        findings, [entry], frozenset({"src/app.py"}), frozenset()
    )
    assert new == [findings[1]]
    assert stale == []
    assert added_entries([entry], [entry, entry]) == [entry]
    assert (
        compare_with_baseline(
            findings,
            [entry.model_copy(update={"family": "M"})],
            frozenset({"src/app.py"}),
            frozenset(),
        )[0]
        == findings
    )
    assert compare_with_baseline(
        findings, [entry, entry], frozenset({"src/app.py"}), frozenset()
    ) == ([], [])
    shifted = scan("src/app.py", "\n" + text, load_policy())
    assert compare_with_baseline(
        shifted, [entry, entry], frozenset({"src/app.py"}), frozenset()
    ) == ([], [entry])
    assert compare_with_baseline(
        scan("src/other.py", text, load_policy()),
        [entry],
        frozenset({"src/other.py"}),
        frozenset(),
    )[0]


def test_required_pattern_and_policy_override() -> None:
    data = load_policy().model_dump()
    assert "ruling_stamp_pattern" in data
    data.pop("ruling_stamp_pattern")
    with pytest.raises(ValidationError):
        ModelHardcodedModelConfigPolicy.model_validate(data)
    policy = load_policy().model_copy(update={"ruling_stamp_pattern": "custom-stamp"})
    assert [f.family for f in scan("src/app.py", 'VALUE = "custom-stamp"', policy)] == [
        "S"
    ]


def test_model_name_fixture(tmp_path: Path) -> None:
    path = tmp_path / "model.py"
    path.write_text('MODEL = "' + "gpt-" + '4"\n')
    assert [
        f.family for f in scan("src/model.py", path.read_text(), load_policy())
    ] == ["M"]


def test_policy_host_name_fixture(tmp_path: Path) -> None:
    host = "fixture-lab.internal"
    policy = load_policy().model_copy(update={"lab_host_names": (host,)})
    path = tmp_path / "host.py"
    path.write_text(f'HOST = "{host}"\n')
    assert [f.family for f in scan("src/host.py", path.read_text(), policy)] == ["D"]
