"""
Tests for infra_bases module.

Validates that infrastructure base imports are accessible and properly exposed.
"""


def test_can_import_infra_bases():
    """Test that infra_bases module imports successfully."""
    from omnibase_core.infrastructure import infra_bases

    assert infra_bases is not None


def test_service_effect_available():
    """Test that ModelServiceEffect is accessible."""
    from omnibase_core.infrastructure.infra_bases import ModelServiceEffect

    assert ModelServiceEffect is not None


def test_service_compute_available():
    """Test that ModelServiceCompute is accessible."""
    from omnibase_core.infrastructure.infra_bases import ModelServiceCompute

    assert ModelServiceCompute is not None


def test_all_exports_defined():
    """Test that __all__ contains expected exports."""
    from omnibase_core.infrastructure import infra_bases

    assert hasattr(infra_bases, "__all__")
    assert "ModelServiceEffect" in infra_bases.__all__
    assert "ModelServiceCompute" in infra_bases.__all__
