import importlib
import sys
from pathlib import Path
from types import ModuleType


class _Dummy:
    pass


def _install_stub_modules():
    # Stub for httpx to satisfy import
    if "httpx" not in sys.modules:
        sys.modules["httpx"] = ModuleType("httpx")

    # Stub server.models.intelligence_models with permissive classes/functions
    models_mod = ModuleType("server.models.intelligence_models")

    class _Model:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        @classmethod
        def create_intelligence_document(cls, **kwargs):
            return cls(**kwargs)

        def model_dump(self, mode: str = "json"):
            return getattr(self, "__dict__", {})

    class AnalysisType:
        ENHANCED_CODE_CHANGES_WITH_CORRELATION = "enhanced"

    class RiskLevel:
        LOW = "low"

    class SecurityStatus:
        CLEAN = "clean"

    # Bind names expected by the script
    models_mod.AnalysisType = AnalysisType
    models_mod.ChangeSummary = _Model
    models_mod.CrossRepositoryCorrelation = _Model
    models_mod.ImpactAssessment = _Model
    models_mod.IntelligenceDocumentContent = _Model
    models_mod.IntelligenceHookConfig = _Model
    models_mod.IntelligenceMetadata = _Model
    models_mod.IntelligenceServiceRequest = _Model
    models_mod.MCPCreateDocumentRequest = _Model
    models_mod.MCPResponse = _Model
    models_mod.RiskLevel = RiskLevel
    models_mod.SecurityAndPrivacy = _Model
    models_mod.SecurityStatus = SecurityStatus
    models_mod.TechnicalAnalysis = _Model

    def create_change_summary(**kwargs):
        return _Model(**kwargs)

    def create_intelligence_metadata(**kwargs):
        return _Model(**kwargs)

    def validate_intelligence_document(doc):
        return True

    models_mod.create_change_summary = create_change_summary
    models_mod.create_intelligence_metadata = create_intelligence_metadata
    models_mod.validate_intelligence_document = validate_intelligence_document

    # Ensure parent packages exist
    server_pkg = sys.modules.setdefault("server", ModuleType("server"))
    models_pkg = sys.modules.setdefault("server.models", ModuleType("server.models"))
    sys.modules["server.models.intelligence_models"] = models_mod
    setattr(models_pkg, "intelligence_models", models_mod)
    setattr(server_pkg, "models", models_pkg)

    # Stub server.config.archon_config
    config_mod = ModuleType("server.config.archon_config")

    class _Svc:
        def __init__(self):
            self.port = 8053

    class _Cfg:
        def __init__(self):
            self.intelligence_service = _Svc()

    def get_archon_config():
        return _Cfg()

    def get_intelligence_endpoint():
        return "http://localhost:8053/extract/document"

    config_mod.get_archon_config = get_archon_config
    config_mod.get_intelligence_endpoint = get_intelligence_endpoint

    config_pkg = sys.modules.setdefault("server.config", ModuleType("server.config"))
    sys.modules["server.config.archon_config"] = config_mod
    setattr(config_pkg, "archon_config", config_mod)
    setattr(server_pkg, "config", config_pkg)


def test_find_matching_commits_builds_or_grep_and_lookback_days(tmp_path: Path):
    _install_stub_modules()

    mod = importlib.import_module("scripts.intelligence.intelligence_hook")

    hook = mod.IntelligenceHook()
    # Force config for lookback days
    hook.config["analysis"]["correlation_lookback_days"] = 5

    captured_cmd = {}

    def fake_run_git(cmd, cwd=None):
        captured_cmd["cmd"] = cmd
        return ""  # no results

    hook.run_git_command = fake_run_git  # type: ignore[method-assign]

    hook._find_matching_commits_in_repo(tmp_path, ["alpha", "beta", "gamma"])  # type: ignore[arg-type]

    cmd = captured_cmd.get("cmd", [])
    assert cmd, "Expected git command to be constructed"
    # Ensure since uses configured lookback days
    assert any(str(x).startswith("--since=5 days ago") for x in cmd)
    # Ensure multiple --grep are present (OR semantics)
    grep_flags = [x for x in cmd if x == "--grep"]
    assert len(grep_flags) >= 1
    # Ensure no single pipe-joined pattern in grep arguments
    # (check arguments that come after --grep flags, not format strings)
    grep_indices = [i for i, x in enumerate(cmd) if x == "--grep"]
    grep_values = [cmd[i + 1] for i in grep_indices if i + 1 < len(cmd)]
    assert not any(
        "|" in str(x) for x in grep_values
    ), f"Found pipe in grep values: {grep_values}"
