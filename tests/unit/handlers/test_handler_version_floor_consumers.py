# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for HandlerVersionFloorConsumers (OMN-19998).

The positive fixture is the 2026-10-15 stall: omnimarket raised its
omnibase-core floor from 0.47.39 to 0.47.44 while omnibase_infra still pinned
0.47.39, so the merge queue of omnibase_infra failed for 6.5 hours.
"""

from __future__ import annotations

import pytest

from omnibase_core.handlers.handler_version_floor_consumers import (
    HandlerVersionFloorConsumers,
    declared_floors,
    parse_version,
)
from omnibase_core.handlers.handler_version_floor_consumers_cli import (
    load_layer_map,
)
from omnibase_core.models.version_drift.model_consumer_pyproject import (
    ModelConsumerPyproject,
)
from omnibase_core.models.version_drift.model_version_floor_check_input import (
    ModelVersionFloorCheckInput,
)

pytestmark = pytest.mark.unit

LAYER_MAP = load_layer_map()


def _market(core_spec: str, infra_spec: str = ">=0.38.72,<0.39.0") -> str:
    return (
        '[project]\nname = "omnimarket"\nversion = "0.4.315"\n'
        f'dependencies = [\n  "omnibase-core{core_spec}",\n'
        f'  "omnibase-infra{infra_spec}",\n  "pydantic>=2",\n]\n'
    )


def _infra(range_spec: str, exact: str | None) -> str:
    text = (
        '[project]\nname = "omnibase-infra"\n'
        f'dependencies = ["omnibase-core{range_spec}"]\n'
    )
    if exact is not None:
        text += f'\n[tool.uv]\noverride-dependencies = ["omnibase-core=={exact}"]\n'
    return text


def _with_market(name: str, core_spec: str) -> str:
    return (
        f'[project]\nname = "{name}"\n'
        f'dependencies = ["omnibase-core{core_spec}", "omnimarket>=0.4"]\n'
    )


def _run(
    base: str | None,
    head: str,
    consumers: tuple[ModelConsumerPyproject, ...],
    repo: str = "omnimarket",
) -> tuple[str, list[str]]:
    report = HandlerVersionFloorConsumers().handle(
        ModelVersionFloorCheckInput(
            repo=repo,
            layer_map=LAYER_MAP,
            base_pyproject=base,
            head_pyproject=head,
            consumers=consumers,
        )
    )
    return report.overall_status, [f.message for f in report.findings]


def _consumer(repo: str, text: str | None) -> ModelConsumerPyproject:
    return ModelConsumerPyproject(repo=repo, ref="origin/dev", pyproject=text)


def test_floor_raise_ahead_of_a_pinned_consumer_fails_and_names_it() -> None:
    status, messages = _run(
        _market(">=0.47.39,<0.48.0"),
        _market(">=0.47.44,<0.48.0"),
        (_consumer("omnibase_infra", _infra(">=0.47.31,<0.48.0", "0.47.39")),),
    )
    assert status == "FAIL"
    assert len(messages) == 1
    assert "omnibase_infra" in messages[0]
    assert "omnibase-core" in messages[0]
    assert "0.47.44" in messages[0]
    assert "0.47.39" in messages[0]


def test_floor_raise_passes_once_every_consumer_pins_at_least_it() -> None:
    status, messages = _run(
        _market(">=0.47.39,<0.48.0"),
        _market(">=0.47.44,<0.48.0"),
        (_consumer("omnibase_infra", _infra(">=0.47.31,<0.48.0", "0.47.44")),),
    )
    assert (status, messages) == ("PASS", [])


def test_a_consumer_of_the_raising_repository_with_a_lower_floor_fails() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer(
                "omniclaude", _with_market("omninode-claude", ">=0.47.31,<0.48.0")
            ),
        ),
    )
    assert status == "FAIL"
    assert "0.47.31" in messages[0]
    assert "installs the raising repository" in messages[0]


def test_a_range_that_admits_the_raise_passes_for_a_non_consumer_of_it() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (_consumer("omnibase_infra", _infra(">=0.47.31,<0.48.0", None)),),
    )
    assert (status, messages) == ("PASS", [])


@pytest.mark.parametrize("spec", ["<0.47.44", "<=0.47.43", "~=0.47.39.0", "==0.47.*"])
def test_an_upper_bound_below_the_raise_fails(spec: str) -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44" if spec != "==0.47.*" else ">=0.48.1"),
        (_consumer("omnibase_infra", _infra(f">=0.47.0,{spec}", None)),),
    )
    assert status == "FAIL"
    assert "below the new floor" in messages[0]


def test_no_floor_raise_needs_no_consumer() -> None:
    status, messages = _run(
        _market(">=0.47.44"),
        _market(">=0.47.44,<0.48.0"),
        (_consumer("omnibase_infra", None),),
    )
    assert (status, messages) == ("PASS", [])


def test_a_lowered_floor_is_not_a_raise() -> None:
    status, _ = _run(
        _market(">=0.47.44"),
        _market(">=0.47.40"),
        (_consumer("omnibase_infra", _infra(">=0.47.31", None)),),
    )
    assert status == "PASS"


def test_an_unreadable_consumer_is_never_assumed_compatible() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (_consumer("omnibase_infra", None),),
    )
    assert status == "FAIL"
    assert "could not be read" in messages[0]


def test_a_consumer_that_does_not_install_the_package_is_not_counted() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer(
                "omnidash", '[project]\nname = "omnidash"\ndependencies = ["httpx"]\n'
            ),
        ),
    )
    assert (status, messages) == ("PASS", [])


def test_the_changing_repository_is_not_its_own_consumer() -> None:
    status, _ = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (_consumer("omnimarket", _market(">=0.47.39")),),
    )
    assert status == "PASS"


def test_a_newly_declared_sibling_dependency_counts_as_a_raise() -> None:
    base = '[project]\nname = "omnimarket"\ndependencies = []\n'
    status, messages = _run(
        base,
        _market(">=0.47.44"),
        (_consumer("omnibase_infra", _infra(">=0.47.31", "0.47.39")),),
    )
    assert status == "FAIL"
    assert "omnibase_infra" in messages[0]


def test_a_consumer_with_no_lower_bound_fails() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer(
                "omniclaude",
                '[project]\nname = "omninode-claude"\n'
                'dependencies = ["omnibase-core", "omnimarket"]\n',
            ),
        ),
    )
    assert status == "FAIL"
    assert "no lower bound" in messages[0]


def test_every_failing_consumer_is_named() -> None:
    status, messages = _run(
        _market(">=0.47.39"),
        _market(">=0.47.44"),
        (
            _consumer("omnibase_infra", _infra(">=0.47.31", "0.47.39")),
            _consumer(
                "omniclaude",
                '[project]\nname = "omninode-claude"\n'
                'dependencies = ["omnibase-core>=0.47.40", "omnimarket"]\n',
            ),
            _consumer(
                "omnibase_internal",
                '[project]\nname = "omnibase-internal"\n'
                '[dependency-groups]\ndev = ["omnibase-core>=0.47.50", "omnimarket"]\n',
            ),
        ),
    )
    assert status == "FAIL"
    named = sorted(m.split(":", 1)[0] for m in messages)
    assert named == ["omnibase_infra", "omniclaude"]


def test_a_third_party_floor_raise_is_not_checked() -> None:
    status, _ = _run(
        '[project]\nname = "omnimarket"\ndependencies = ["pydantic>=2.0"]\n',
        '[project]\nname = "omnimarket"\ndependencies = ["pydantic>=2.12"]\n',
        (_consumer("omnibase_infra", _infra(">=0.47.31", None)),),
    )
    assert status == "PASS"


def test_an_undeclared_repository_is_an_error() -> None:
    status, _ = _run(None, _market(">=0.47.44"), (), repo="not_a_registry_repo")
    assert status == "ERROR"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("0.47.44", (0, 47, 44)),
        ("0.48.0", (0, 48)),
        ("1.0rc1", (1,)),
        ("v2.3", (2, 3)),
    ],
)
def test_parse_version(text: str, expected: tuple[int, ...]) -> None:
    assert parse_version(text) == expected


def test_declared_floors_take_the_highest_lower_bound_across_tables() -> None:
    floors = declared_floors(_infra(">=0.47.31,<0.48.0", "0.47.39"))
    assert floors["omnibase-core"].floor == (0, 47, 39)
