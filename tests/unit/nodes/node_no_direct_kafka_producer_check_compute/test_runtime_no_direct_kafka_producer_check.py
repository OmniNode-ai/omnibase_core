# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the no-direct-kafka-producer-check CLI runtime (OMN-14659, OMN-13305 pattern).

Covers both invocation modes: pre-commit's explicit-filenames mode (I/O read
directly at the CLI boundary) and the full-tree walk mode (delegated to
``node_source_file_gather_effect``) — both dispatch to the SAME canonical
``NodeNoDirectKafkaProducerCheckCompute`` handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from omnibase_core.nodes.node_no_direct_kafka_producer_check_compute.runtime_no_direct_kafka_producer_check import (
    main,
)

pytestmark = pytest.mark.unit


def test_main_filenames_mode_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text("from omniclaude.publisher import Publisher\n")

    exit_code = main([str(clean)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert (
        "OK: No direct Kafka producer usage found outside the shared publisher layer"
        in out
    )


def test_main_filenames_mode_fail(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text("import confluent_kafka\n")

    exit_code = main([str(bad)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 direct Kafka producer violation(s):" in out
    assert "confluent_kafka" in out


def test_main_filenames_mode_skips_non_python_and_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    not_python = tmp_path / "notes.md"
    not_python.write_text("KafkaProducer mentioned in prose\n")
    missing = tmp_path / "missing.py"

    exit_code = main([str(not_python), str(missing)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert (
        "OK: No direct Kafka producer usage found outside the shared publisher layer"
        in out
    )


def test_main_full_tree_mode_walks_root(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "bad.py").write_text("producer = KafkaProducer(bootstrap_servers=host)\n")
    (src / "clean.py").write_text("from omniclaude.publisher import Publisher\n")

    exit_code = main(["--root", str(src)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 direct Kafka producer violation(s):" in out
    assert "bad.py" in out


def test_main_full_tree_mode_empty_root_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    exit_code = main(["--root", str(empty_root)])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert (
        "OK: No direct Kafka producer usage found outside the shared publisher layer"
        in out
    )


def test_main_syntax_error_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n    pass\n")

    exit_code = main([str(broken)])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "FAIL: Found 1 direct Kafka producer violation(s):" in out
