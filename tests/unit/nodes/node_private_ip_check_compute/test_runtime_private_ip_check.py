# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Runtime parity, report persistence and runtime diagnostics."""

from pathlib import Path
from unittest.mock import patch

import pytest

from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_input import (
    ModelSourceFileGatherInput,
)
from omnibase_core.models.nodes.source_file_gather.model_source_file_gather_output import (
    ModelSourceFileGatherOutput,
)
from omnibase_core.models.validation.model_validation_report import (
    ModelValidationReport,
)
from omnibase_core.nodes.node_private_ip_check_compute.runtime_private_ip_check import (
    main,
)
from omnibase_core.nodes.node_source_file_gather_effect.handler import (
    NodeSourceFileGatherEffect,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("directory", [False, True])
def test_parity_runtime_effect_decode_policy(
    parity_corpus: Path, directory: bool
) -> None:
    original = NodeSourceFileGatherEffect.handle
    requests: list[ModelSourceFileGatherInput] = []

    def record(
        self: NodeSourceFileGatherEffect, request: ModelSourceFileGatherInput
    ) -> ModelSourceFileGatherOutput:
        requests.append(request)
        return original(self, request)

    path = parity_corpus if directory else parity_corpus / "blocks.py"
    with patch.object(NodeSourceFileGatherEffect, "handle", record):
        assert main([str(path), "-q"]) == 1
    assert requests
    assert all(request.decode_errors == "replace" for request in requests)


@pytest.mark.parametrize(
    ("name", "status", "code"), [("blocks.py", "FAIL", 1), ("public.py", "PASS", 0)]
)
def test_parity_runtime_filenames(
    parity_corpus: Path, tmp_path: Path, name: str, status: str, code: int
) -> None:
    report = tmp_path / "result.json"
    assert main([str(parity_corpus / name), "--report-json", str(report)]) == code
    assert (
        ModelValidationReport.model_validate_json(report.read_text()).overall_status
        == status
    )


def test_parity_runtime_zero_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    report = tmp_path / "result.json"
    assert main(["--root", str(root), "--report-json", str(report)]) == 0
    result = ModelValidationReport.model_validate_json(report.read_text())
    assert result.overall_status == "ERROR"
    assert result.metrics.error_count == 1
    capsys.readouterr()


def test_parity_runtime_unreadable(
    parity_corpus: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = parity_corpus / "blocks.py"
    report = tmp_path / "result.json"
    original = Path.read_text

    def denied(self: Path, *args: object, **kwargs: object) -> str:
        if self == path:
            raise PermissionError("fixture access denied")
        return original(self)

    with patch.object(Path, "read_text", denied):
        code = main([str(path), "--report-json", str(report)])
        output = capsys.readouterr().out
    # The replaced runtime exited 0 with this line when a file could not be read.
    assert (code, output) == (0, "No hardcoded private-IP violations found.\n")
    assert (
        ModelValidationReport.model_validate_json(report.read_text()).overall_status
        == "ERROR"
    )


@pytest.mark.parametrize("directory", [False, True])
def test_parity_runtime_invalid_utf8(
    tmp_path: Path, directory: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "source"
    root.mkdir()
    source = root / "encoded.py"
    address = ".".join(str(part) for part in (10, 0, 0, 1))
    source.write_bytes(b"prefix\xff " + address.encode() + b"\r\n")
    report = tmp_path / "report.json"
    paths = [str(root if directory else source)]
    code = main([*paths, "--report-json", str(report)])
    output = capsys.readouterr().out
    expected = (
        f"{source}:1:9: [10/8] {address!r}\n"
        f"  prefix\ufffd {address}\n"
        "\n1 hardcoded private-IP violation(s). Resolve the "
        "endpoint from the routing authority / contract, or add "
        "`# " + "onex-" + "allow-internal-ip` to suppress an approved fixture.\n"
    )
    assert (code, output) == (1, expected)
    assert (
        ModelValidationReport.model_validate_json(report.read_text()).overall_status
        == "FAIL"
    )
