import importlib.util
import signal
from pathlib import Path

import pytest


def import_module_from_path(path: Path):
    spec = importlib.util.spec_from_file_location(
        "validate_contracts_module", str(path)
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_setup_timeout_handler_uses_constant_message():
    # Skip on platforms without SIGALRM
    if not hasattr(signal, "SIGALRM"):
        pytest.skip("SIGALRM not available on this platform")

    module_path = Path("scripts/validation/validate-contracts.py").resolve()
    module = import_module_from_path(module_path)

    # Install handler
    module.setup_timeout_handler()

    # Retrieve installed handler and call it directly to assert message
    handler = signal.getsignal(signal.SIGALRM)
    assert handler is not None

    with pytest.raises(TimeoutError) as ei:
        # type: ignore[misc]
        handler(14, None)  # type: ignore[call-arg]

    assert module.TIMEOUT_ERROR_MESSAGE in str(ei.value)
